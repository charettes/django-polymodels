import threading
from collections import defaultdict, namedtuple
from operator import attrgetter

from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.db.models.constants import LOOKUP_SEP
from django.db.models.signals import class_prepared
from django.utils.functional import cached_property

from .managers import PolymorphicManager
from .utils import copy_fields, get_content_type, get_content_types


class SubclassAccessor(namedtuple('SubclassAccessor', ['attrs', 'proxy', 'related_lookup'])):
    @staticmethod
    def _identity(obj):
        return obj

    @cached_property
    def attrgetter(self):
        if not self.attrs:
            return self._identity
        return attrgetter('.'.join(self.attrs))

    def __call__(self, obj, with_prefetched_objects=False):
        # Cast to the right concrete model by going up in the
        # SingleRelatedObjectDescriptor chain
        casted = self.attrgetter(obj)
        # If it's a proxy model we make sure to type cast it
        proxy = self.proxy
        if proxy:
            casted = copy_fields(casted, proxy)
        if with_prefetched_objects:
            try:
                casted._prefetched_objects_cache.update(obj._prefetched_objects_cache)
            except AttributeError:
                casted._prefetched_objects_cache = obj._prefetched_objects_cache
        return casted


EMPTY_ACCESSOR = SubclassAccessor((), None, '')


class SubclassAccessors(defaultdict):
    def __init__(self):
        self.model = None
        self.apps = None

    def contribute_to_class(self, model, name, **kwargs):
        self.model = model
        self.apps = model._meta.apps
        self.lock = threading.RLock()
        setattr(model, name, self)
        # Ideally we would connect to the model.apps.clear_cache()
        class_prepared.connect(self.class_prepared_receiver, weak=False)

    def class_prepared_receiver(self, sender, **kwargs):
        if issubclass(sender, self.model):
            with self.lock:
                for parent in sender._meta.parents:
                    self.pop(self.get_model_key(parent._meta), None)

    def get_model_key(self, opts):
        return opts.app_label, opts.model_name

    def __get__(self, instance, owner):
        if owner is self.model:
            return self
        opts = owner._meta
        model_key = self.get_model_key(opts)
        return self[model_key]

    def __missing__(self, model_key):
        """
        Generate the accessors for this model by recursively generating its
        children accessors and prefixing them.
        """
        owner = self.apps.get_model(*model_key)
        if not issubclass(owner, self.model):
            raise KeyError
        accessors = {owner: EMPTY_ACCESSOR}
        with self.lock:
            for model in self.apps.get_models():
                opts = model._meta
                if opts.proxy and issubclass(model, owner) and (owner._meta.proxy or opts.concrete_model is owner):
                    accessors[model] = SubclassAccessor((), model, '')
                # Use .get() instead of `in` as proxy inheritance is also
                # stored in _meta.parents as None.
                elif opts.parents.get(owner):
                    part = opts.model_name
                    for child, (parts, proxy, _lookup) in self[self.get_model_key(opts)].items():
                        accessors[child] = SubclassAccessor((part,) + parts, proxy, LOOKUP_SEP.join((part,) + parts))
        return accessors


class BasePolymorphicModel(models.Model):
    class Meta:
        abstract = True

    subclass_accessors = SubclassAccessors()

    def type_cast(self, to=None, with_prefetched_objects=False):
        if to is None:
            content_type_id = getattr(self, "%s_id" % self.CONTENT_TYPE_FIELD)
            to = ContentType.objects.get_for_id(content_type_id).model_class()
        accessor = self.subclass_accessors[to]
        return accessor(self, with_prefetched_objects)

    def save(self, *args, **kwargs):
        if self._state.adding and getattr(self, self.CONTENT_TYPE_FIELD, None) is None:
            content_type = get_content_type(self.__class__)
            setattr(self, self.CONTENT_TYPE_FIELD, content_type)
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        kept_parent = None
        if keep_parents:
            parent_ptr = next(iter(self._meta.concrete_model._meta.parents.values()), None)
            if parent_ptr:
                kept_parent = getattr(self, parent_ptr.name)
        if kept_parent:
            context_manager = transaction.atomic(using=using, savepoint=False)
        else:
            context_manager = transaction.mark_for_rollback_on_error(using=using)
        with context_manager:
            deletion = super().delete(using=using, keep_parents=keep_parents)
            if kept_parent:
                parent_content_type = get_content_type(kept_parent)
                setattr(kept_parent, self.CONTENT_TYPE_FIELD, parent_content_type)
                kept_parent.save(update_fields=[self.CONTENT_TYPE_FIELD])
        return deletion

    @classmethod
    def content_type_lookup(cls, *models, **kwargs):
        query_name = kwargs.pop('query_name', None) or cls.CONTENT_TYPE_FIELD
        if models:
            query_name = "%s__in" % query_name
            value = set(ct.pk for ct in get_content_types(*models).values())
        else:
            value = get_content_type(cls).pk
        return {query_name: value}

    @classmethod
    def subclasses_lookup(cls, query_name=None):
        return cls.content_type_lookup(
            cls, *tuple(cls.subclass_accessors), query_name=query_name
        )

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        try:
            content_type_field_name = getattr(cls, 'CONTENT_TYPE_FIELD')
        except AttributeError:
            errors.append(checks.Error(
                '`BasePolymorphicModel` subclasses must define a `CONTENT_TYPE_FIELD`.',
                hint=None,
                obj=cls,
                id='polymodels.E001',
            ))
        else:
            try:
                content_type_field = cls._meta.get_field(content_type_field_name)
            except FieldDoesNotExist:
                errors.append(checks.Error(
                    "`CONTENT_TYPE_FIELD` points to an inexistent field '%s'." % content_type_field_name,
                    hint=None,
                    obj=cls,
                    id='polymodels.E002',
                ))
            else:
                if (not isinstance(content_type_field, models.ForeignKey) or
                        content_type_field.remote_field.model is not ContentType):
                    errors.append(checks.Error(
                        "`%s` must be a `ForeignKey` to `ContentType`." % content_type_field_name,
                        hint=None,
                        obj=content_type_field,
                        id='polymodels.E003',
                    ))
        return errors


class PolymorphicModel(BasePolymorphicModel):
    CONTENT_TYPE_FIELD = 'content_type'
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')

    objects = PolymorphicManager()

    class Meta:
        abstract = True

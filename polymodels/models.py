from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import FieldDoesNotExist
from django.db.models.signals import class_prepared

from .compat import get_remote_field, get_remote_model
from .managers import PolymorphicManager
from .utils import copy_fields, get_content_type, get_content_types

EMPTY_ACCESSOR = ((), None, '')


class SubclassAccessors(object):
    def __init__(self):
        self.cache = {}
        self.model = None
        self.name = None

    def contribute_to_class(self, model, name, **kwargs):
        self.model = model
        self.name = name
        setattr(model, name, self)
        # Ideally we would connect to the model.apps.clear_cache()
        class_prepared.connect(self.class_prepared_receiver, weak=False)

    def get_cache_key(self, opts):
        return opts.app_label, opts.model_name

    def class_prepared_receiver(self, sender, **kwargs):
        if issubclass(sender, self.model):
            for parent in sender._meta.parents:
                self.cache.pop(self.get_cache_key(parent._meta), None)

    def cache_accessors(self, model):
        parents = [model]
        opts = model._meta
        accessors = self.cache.setdefault(self.get_cache_key(opts), {})
        proxy = model if opts.proxy else None
        parts = []
        while parents:
            parent = parents.pop(0)
            if issubclass(parent, self.model):
                parent_opts = parent._meta
                parent_accessors = self.cache.setdefault(self.get_cache_key(parent_opts), {})
                parent_accessors[model] = (tuple(parts), proxy, LOOKUP_SEP.join(parts))
                if parent_opts.proxy:
                    parents.insert(0, parent_opts.proxy_for_model)
                else:
                    parts.insert(0, parent_opts.model_name)
                    parents = list(parent_opts.parents) + parents
        return accessors

    def __get__(self, instance, owner):
        opts = owner._meta
        cache_key = self.get_cache_key(opts)
        try:
            return self.cache[cache_key]
        except KeyError:
            for model in opts.apps.get_models():
                if issubclass(model, owner):
                    self.cache_accessors(model)
        return self.cache_accessors(owner)


class BasePolymorphicModel(models.Model):
    class Meta:
        abstract = True

    subclass_accessors = SubclassAccessors()

    def type_cast(self, to=None):
        if to is None:
            content_type_id = getattr(self, "%s_id" % self.CONTENT_TYPE_FIELD)
            to = ContentType.objects.get_for_id(content_type_id).model_class()
        attrs, proxy, _lookup = self.subclass_accessors.get(to, EMPTY_ACCESSOR)
        # Cast to the right concrete model by going up in the
        # SingleRelatedObjectDescriptor chain
        type_casted = self
        for attr in attrs:
            type_casted = getattr(type_casted, attr)
        # If it's a proxy model we make sure to type cast it
        if proxy:
            type_casted = copy_fields(type_casted, proxy)
        return type_casted

    def save(self, *args, **kwargs):
        if self.pk is None:
            content_type = get_content_type(self.__class__)
            setattr(self, self.CONTENT_TYPE_FIELD, content_type)
        return super(BasePolymorphicModel, self).save(*args, **kwargs)

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
        errors = super(BasePolymorphicModel, cls).check(**kwargs)
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
                        get_remote_model(get_remote_field(content_type_field)) is not ContentType):
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

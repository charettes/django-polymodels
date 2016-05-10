from __future__ import unicode_literals

import threading
from collections import defaultdict

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
                    accessors[model] = ((), model, '')
                # Use .get() instead of `in` as proxy inheritance is also
                # stored in _meta.parents as None.
                elif opts.parents.get(owner):
                    part = opts.model_name
                    for child, (parts, proxy, _lookup) in self[self.get_model_key(opts)].items():
                        accessors[child] = ((part,) + parts, proxy, LOOKUP_SEP.join((part,) + parts))
        return accessors


class BasePolymorphicModel(models.Model):
    class Meta:
        abstract = True

    subclass_accessors = SubclassAccessors()

    def type_cast(self, to=None):
        if to is None:
            content_type_id = getattr(self, "%s_id" % self.CONTENT_TYPE_FIELD)
            to = ContentType.objects.get_for_id(content_type_id).model_class()
        attrs, proxy, _lookup = self.subclass_accessors[to]
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

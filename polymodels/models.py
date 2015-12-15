from __future__ import unicode_literals

from django.apps import apps as global_apps
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import FieldDoesNotExist

from .compat import get_remote_field, get_remote_model
from .managers import PolymorphicManager
from .utils import copy_fields, get_content_type, get_content_types

EMPTY_ACCESSOR = ([], None, '')


class BasePolymorphicModel(models.Model):
    class Meta:
        abstract = True

    def type_cast(self, to=None):
        if to is None:
            content_type_id = getattr(self, "%s_id" % self.CONTENT_TYPE_FIELD)
            to = ContentType.objects.get_for_id(content_type_id).model_class()
        attrs, proxy, _lookup = self._meta._subclass_accessors.get(to, EMPTY_ACCESSOR)
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
            cls, *tuple(cls._meta._subclass_accessors.keys()),
            query_name=query_name
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


def prepare_polymorphic_model(sender, **kwargs):
    if issubclass(sender, BasePolymorphicModel):
        opts = sender._meta
        try:
            global_apps.get_app_config(opts.app_label)
        except LookupError:
            # Models registered to non-installed application should not be
            # considered as Django will ignore them by default.
            return
        setattr(opts, '_subclass_accessors', {})
        parents = [sender]
        proxy = sender if opts.proxy else None
        attrs = []
        while parents:
            parent = parents.pop(0)
            if issubclass(parent, BasePolymorphicModel):
                parent_opts = parent._meta
                lookup = LOOKUP_SEP.join(attrs)
                parent_opts._subclass_accessors[sender] = (tuple(attrs), proxy, lookup)
                if parent_opts.proxy:
                    parents.insert(0, parent_opts.proxy_for_model)
                else:
                    attrs.insert(0, parent_opts.model_name)
                    parents = list(parent._meta.parents.keys()) + parents

models.signals.class_prepared.connect(prepare_polymorphic_model)

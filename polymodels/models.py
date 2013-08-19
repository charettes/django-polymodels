from __future__ import unicode_literals

import django
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import models
try:
    from django.db.models.constants import LOOKUP_SEP
except ImportError:  # TODO: Remove when support for Django 1.4 is dropped
    from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.fields import FieldDoesNotExist

from .managers import PolymorphicManager
from .utils import copy_fields, get_content_type, model_name, proxy_for_model


EMPTY_ACCESSOR = ([], None, '')


class BasePolymorphicModel(models.Model):
    class Meta:
        abstract = True

    def type_cast(self, to=None):
        if to is None:
            to = getattr(self, self.CONTENT_TYPE_FIELD).model_class()
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
            content_type = get_content_type(self.__class__, self._state.db)
            setattr(self, self.CONTENT_TYPE_FIELD, content_type)
        return super(BasePolymorphicModel, self).save(*args, **kwargs)


class PolymorphicModel(BasePolymorphicModel):
    CONTENT_TYPE_FIELD = 'content_type'
    content_type = models.ForeignKey(ContentType, related_name='+')

    objects = PolymorphicManager()

    class Meta:
        abstract = True


def prepare_polymorphic_model(sender, **kwargs):
    if issubclass(sender, BasePolymorphicModel):
        opts = sender._meta
        try:
            content_type_field_name = getattr(sender, 'CONTENT_TYPE_FIELD')
        except AttributeError:
            raise ImproperlyConfigured('`BasePolymorphicModel` subclasses must '
                                       'define a `CONTENT_TYPE_FIELD`.')
        else:
            try:
                content_type_field = opts.get_field(content_type_field_name)
            except FieldDoesNotExist:
                raise ImproperlyConfigured('`%s.%s.CONTENT_TYPE_FIELD` '
                                           'points to an inexistent field "%s".'
                                           % (sender.__module__,
                                              sender.__name__,
                                              content_type_field_name))
            else:
                if (not isinstance(content_type_field, models.ForeignKey) or
                    content_type_field.rel.to is not ContentType):
                    raise ImproperlyConfigured('`%s.%s.%s` must be a '
                                               '`ForeignKey` to `ContentType`.'
                                               % (sender.__module__,
                                                  sender.__name__,
                                                  content_type_field_name))
        setattr(opts, '_subclass_accessors', {})
        parents = [sender]
        proxy = sender if opts.proxy else None
        attrs = []
        while parents:
            parent = parents.pop(0)
            if issubclass(parent, BasePolymorphicModel):
                parent_opts = parent._meta
                # We can't do `select_related` on multiple one-to-one
                # relationships on django < 1.6
                # see https://code.djangoproject.com/ticket/16572 and
                # https://code.djangoproject.com/ticket/13781
                if django.VERSION < (1, 6):
                    lookup = LOOKUP_SEP.join(attrs[0:1])
                else:
                    lookup = LOOKUP_SEP.join(attrs)
                parent_opts._subclass_accessors[sender] = (tuple(attrs), proxy, lookup)
                if parent_opts.proxy:
                    parents.insert(0, proxy_for_model(parent))
                else:
                    attrs.insert(0, model_name(parent_opts))
                    parents = list(parent._meta.parents.keys()) + parents

models.signals.class_prepared.connect(prepare_polymorphic_model)

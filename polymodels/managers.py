from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .utils import get_content_type, get_content_types


class PolymorphicQuerySet(models.query.QuerySet):
    def select_subclasses(self, *args):
        self.type_cast = True
        content_type_field_name = self.model.CONTENT_TYPE_FIELD
        lookups = set([content_type_field_name])
        opts = self.model._meta
        accessors = opts._subclass_accessors
        if args:
            subclasses = set()
            # Collect all subclasses
            for subclass in args:
                if not issubclass(subclass, self.model):
                    raise TypeError("%r is not a subclass of %r" % (subclass,
                                                                    self.model))
                subclasses.update(subclass._meta._subclass_accessors.keys())
            # Collect all `select_related` required lookups
            for subclass in subclasses:
                # Avoid collecting ourself and proxy subclasses
                subclass_lookup = accessors[subclass][2]
                if subclass_lookup:
                    lookups.add(subclass_lookup)
            # Fetch associated `ContentType` instances for filtering
            content_types = get_content_types(subclasses)
            filters = {"%s__in" % content_type_field_name:
                       tuple(ct.pk for ct in content_types.values())}
            qs = self.filter(**filters)
        else:
            # Collect all `select_related` required lookups
            for accessor in accessors.values():
                # Avoid collecting ourself and proxy subclasses
                if accessor[2]:
                    lookups.add(accessor[2])
            qs = self
        return qs.select_related(*lookups)

    def exclude_subclasses(self):
        content_type_field_name = self.model.CONTENT_TYPE_FIELD
        model_content_type = get_content_type(self.model)
        return self.filter(**{content_type_field_name: model_content_type})

    def _clone(self, *args, **kwargs):
        kwargs.update(type_cast=getattr(self, 'type_cast', False))
        return super(PolymorphicQuerySet, self)._clone(*args, **kwargs)

    def iterator(self):
        iterator = super(PolymorphicQuerySet, self).iterator()
        if getattr(self, 'type_cast', False):
            for obj in iterator:
                yield obj.type_cast()
        else:
            # yield from iterator
            for obj in iterator:
                yield obj

class PolymorphicManager(models.Manager):
    use_for_related_fields = True

    def contribute_to_class(self, model, name):
        # Avoid circular reference
        from .models import BasePolymorphicModel
        if not issubclass(model, BasePolymorphicModel):
            raise ImproperlyConfigured('`PolymorphicManager` can only be used '
                                       'on `BasePolymorphicModel` subclasses.')
        return super(PolymorphicManager, self).contribute_to_class(model, name)

    def get_query_set(self):
        return PolymorphicQuerySet(self.model, using=self._db)

    def select_subclasses(self, *subclasses):
        return self.get_query_set().select_subclasses(*subclasses)

    def exclude_subclasses(self):
        return self.get_query_set().exclude_subclasses()


from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .utils import get_content_types


class PolymorphicQuerySet(models.query.QuerySet):

    def select_subclasses(self, *subclasses):
        self.type_cast = True
        content_type_field_name = self.model.content_type_field_name
        lookups = set([self.model.content_type_field_name])
        opts = self.model._meta
        accessors = opts._subclass_accessors
        if subclasses:
            sub_subclasses = set()
            for subclass in subclasses:
                if not issubclass(subclass, self.model):
                    raise TypeError("%r is not a subclass of %r" % (subclass,
                                                                    self.model))
                sub_subclasses.update(subclass._meta._subclass_accessors.iterkeys())
                lookups.add(accessors[subclass][2])
            content_types = [ct.pk for cls, ct in get_content_types(sub_subclasses).iteritems()]
            filters = {"%s__in" % content_type_field_name: content_types}
            qs = self.filter(**filters)
        else:
            lookups.update(accessor[2] for accessor in accessors.itervalues())
            qs = self
        return qs.select_related(*lookups)

    def _clone(self, **kwargs):
        kwargs.update(type_cast=getattr(self, 'type_cast', False))
        return super(PolymorphicQuerySet, self)._clone(**kwargs)

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

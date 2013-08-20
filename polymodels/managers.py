from __future__ import unicode_literals
import warnings

import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .utils import get_queryset


class PolymorphicQuerySet(models.query.QuerySet):
    def select_subclasses(self, *subclasses):
        self.type_cast = True
        related = set([self.model.CONTENT_TYPE_FIELD])
        opts = self.model._meta
        accessors = opts._subclass_accessors
        if subclasses:
            qs = self.filter(**self.model.subclasses_lookup(*subclasses))
            # Collect all `select_related` required lookups
            for subclass in subclasses:
                # Avoid collecting ourself and proxy subclasses
                subclass_lookup = accessors[subclass][2]
                if subclass_lookup:
                    related.add(subclass_lookup)
        else:
            # Collect all `select_related` required related
            for accessor in accessors.values():
                # Avoid collecting ourself and proxy subclasses
                if accessor[2]:
                    related.add(accessor[2])
            qs = self
        return qs.select_related(*related)

    def exclude_subclasses(self):
        return self.filter(**self.model.content_type_lookup())

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
            raise ImproperlyConfigured(
                '`%s` can only be used on '
                '`BasePolymorphicModel` subclasses.' % self.__class__.__name__
            )
        return super(PolymorphicManager, self).contribute_to_class(model, name)

    def get_queryset(self):
        model = self.model
        qs = PolymorphicQuerySet(model, using=self._db)
        opts = model._meta
        if opts.proxy:
            # Select only associated model and it's subclasses
            qs = qs.filter(**self.model.subclasses_lookup())
        return qs

    if django.VERSION < (1, 8):
        if django.VERSION >= (1, 6):
            def get_query_set(self):
                warnings.warn(
                    "`PolymorphicManager.get_query_set` is deprecated, use "
                    "`get_queryset` instead",
                    DeprecationWarning if django.VERSION >= (1, 7)
                        else PendingDeprecationWarning,
                    stacklevel=2
                )
                return PolymorphicManager.get_queryset(self)
        else:
            get_query_set = get_queryset

    def select_subclasses(self, *args):
        return get_queryset(self).select_subclasses(*args)

    def exclude_subclasses(self):
        return get_queryset(self).exclude_subclasses()

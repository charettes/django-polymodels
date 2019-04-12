from __future__ import unicode_literals

from functools import partial
from operator import methodcaller

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.query import ModelIterable
from django.utils.six.moves import map

type_cast_iterator = partial(map, methodcaller('type_cast'))
type_cast_prefetch_iterator = partial(map, methodcaller('type_cast', with_prefetched_objects=True))


class PolymorphicModelIterable(ModelIterable):
    def __init__(self, queryset, type_cast=True, **kwargs):
        self.type_cast = type_cast
        super(PolymorphicModelIterable, self).__init__(queryset, **kwargs)

    def __iter__(self):
        iterator = super(PolymorphicModelIterable, self).__iter__()
        if self.type_cast:
            iterator = type_cast_iterator(iterator)
        return iterator


class PolymorphicQuerySet(models.query.QuerySet):
    def select_subclasses(self, *models):
        if issubclass(self._iterable_class, ModelIterable):
            self._iterable_class = PolymorphicModelIterable
        related_lookups = set()
        accessors = self.model.subclass_accessors
        if models:
            subclasses = set()
            for model in models:
                if not issubclass(model, self.model):
                    raise TypeError(
                        "%r is not a subclass of %r" % (model, self.model)
                    )
                subclasses.update(model.subclass_accessors)
            # Collect all `select_related` required lookups
            for subclass in subclasses:
                # Avoid collecting ourself and proxy subclasses
                related_lookup = accessors[subclass].related_lookup
                if related_lookup:
                    related_lookups.add(related_lookup)
            queryset = self.filter(
                **self.model.content_type_lookup(*tuple(subclasses))
            )
        else:
            # Collect all `select_related` required relateds
            for accessor in accessors.values():
                # Avoid collecting ourself and proxy subclasses
                related_lookup = accessor.related_lookup
                if related_lookup:
                    related_lookups.add(related_lookup)
            queryset = self
        if related_lookups:
            queryset = queryset.select_related(*related_lookups)
        return queryset

    def exclude_subclasses(self):
        return self.filter(**self.model.content_type_lookup())

    def _fetch_all(self):
        # Override _fetch_all in order to disable PolymorphicModelIterable's
        # type casting when prefetch_related is used because the latter might
        # crash or disfunction when dealing with a mixed set of objects.
        prefetch_related_objects = self._prefetch_related_lookups and not self._prefetch_done
        type_cast = False
        if self._result_cache is None:
            iterable_class = self._iterable_class
            if issubclass(iterable_class, PolymorphicModelIterable):
                type_cast = bool(prefetch_related_objects)
                iterable_class = partial(iterable_class, type_cast=not type_cast)
            self._result_cache = list(iterable_class(self))
        if prefetch_related_objects:
            self._prefetch_related_objects()
            if type_cast:
                self._result_cache = list(type_cast_prefetch_iterator(self._result_cache))


class PolymorphicManager(models.Manager.from_queryset(PolymorphicQuerySet)):
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
        queryset = super(PolymorphicManager, self).get_queryset()
        model = self.model
        if model._meta.proxy:
            # Select only associated model and its subclasses.
            queryset = queryset.filter(**self.model.subclasses_lookup())
        return queryset

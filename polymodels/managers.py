from __future__ import unicode_literals

import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from .compat import is_model_iterable


try:
    from django.db.models.query import ModelIterable
except ImportError:
    # TODO: Remove when dropping support for Django 1.8.
    class PolymorphicModelIterable(object):
        def __init__(self, iterable):
            self.iterable = iterable

        def __iter__(self):
            for instance in self.iterable:
                yield instance.type_cast()
else:
    class PolymorphicModelIterable(ModelIterable):
        def __iter__(self):
            for instance in super(PolymorphicModelIterable, self).__iter__():
                yield instance.type_cast()


class PolymorphicQuerySet(models.query.QuerySet):
    def select_subclasses(self, *models):
        if is_model_iterable(self):
            self._iterable_class = PolymorphicModelIterable
        relateds = set()
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
                related = accessors[subclass][2]
                if related:
                    relateds.add(related)
            queryset = self.filter(
                **self.model.content_type_lookup(*tuple(subclasses))
            )
        else:
            # Collect all `select_related` required relateds
            for accessor in accessors.values():
                # Avoid collecting ourself and proxy subclasses
                related = accessor[2]
                if accessor[2]:
                    relateds.add(related)
            queryset = self
        if relateds:
            queryset = queryset.select_related(*relateds)
        return queryset

    def exclude_subclasses(self):
        return self.filter(**self.model.content_type_lookup())

    # TODO: Remove when dropping support for Django 1.8.
    if django.VERSION < (1, 9):
        def _clone(self, *args, **kwargs):
            kwargs.update(_iterable_class=getattr(self, '_iterable_class', None))
            return super(PolymorphicQuerySet, self)._clone(*args, **kwargs)

        def iterator(self):
            iterator = super(PolymorphicQuerySet, self).iterator()
            if getattr(self, '_iterable_class', None) is PolymorphicModelIterable:
                return self._iterable_class(iterator)
            return iterator


class PolymorphicManager(models.Manager.from_queryset(PolymorphicQuerySet)):
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
        queryset = super(PolymorphicManager, self).get_queryset()
        model = self.model
        opts = model._meta
        if opts.proxy:
            # Select only associated model and its subclasses.
            queryset = queryset.filter(**self.model.subclasses_lookup())
        return queryset

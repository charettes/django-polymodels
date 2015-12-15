from __future__ import unicode_literals

from django.apps import apps
from django.apps.config import AppConfig
from django.db.models.constants import LOOKUP_SEP


class PolymodelsConfig(AppConfig):
    name = 'polymodels'

    def ready(self):
        from .models import BasePolymorphicModel

        cached = set()

        def cache_subclass_accessors(model):
            cached.add(model)
            opts = model._meta
            setattr(opts, '_subclass_accessors', {})
            parents = [model]
            proxy = model if opts.proxy else None
            attrs = []
            while parents:
                parent = parents.pop(0)
                if issubclass(parent, BasePolymorphicModel):
                    if parent not in cached:
                        cache_subclass_accessors(parent)
                    parent_opts = parent._meta
                    lookup = LOOKUP_SEP.join(attrs)
                    parent_opts._subclass_accessors[model] = (tuple(attrs), proxy, lookup)
                    if parent_opts.proxy:
                        parents.insert(0, parent_opts.proxy_for_model)
                    else:
                        attrs.insert(0, parent_opts.model_name)
                        parents = list(parent._meta.parents.keys()) + parents

        for model in apps.get_models():
            if issubclass(model, BasePolymorphicModel):
                if model not in cached:
                    cache_subclass_accessors(model)

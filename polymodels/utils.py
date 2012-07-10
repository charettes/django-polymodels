
import django
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_unicode


# Prior to #18399 being fixed there was no way to retrieve `ContentType`
# of proxy models while caching it. This is a shim that tries to use the
# newly introduced flag and fallback to another method.
if django.VERSION >= (1, 5):
    # django 1.5 introduced the `for_concrete_models?` kwarg
    def get_content_type(model, db=None):
        manager = ContentType.objects.db_manager(db)
        return manager.get_for_model(model, for_concrete_model=False)

    def get_content_types(models, db=None):
        manager = ContentType.objects.db_manager(db)
        return manager.get_for_models(*models, for_concrete_models=False)
else: # TODO: Remove when support for 1.4 is dropped
    def _get_for_concrete_model(manager, model):
        return manager.get_for_model(model)

    if django.VERSION >= (1, 4):
        # django 1.4 introduced `get_for_models` and `_get_from_cache`
        def _get_from_cache(manager, opts):
            return manager._get_from_cache(opts)

        def _get_for_concrete_models(manager, models):
            return manager.get_for_models(*models)
    else: # TODO: Remove when support for 1.3 is dropped
        def _get_from_cache(manager, opts):
            key = (opts.app_label, opts.object_name.lower())
            return manager.__class__._cache[manager.db][key]

        def _get_for_concrete_models(manager, models):
            content_types = {}
            for model in models:
                content_types[model] = _get_for_concrete_model(manager, model)
            return content_types

    def _get_for_proxy_model(manager, opts, model):
        if model._deferred:
            opts = opts.proxy_for_model._meta
        try:
            return _get_from_cache(manager, opts)
        except KeyError:
            ct, _created = manager.get_or_create(
                app_label = opts.app_label,
                model = opts.object_name.lower(),
                defaults = {'name': smart_unicode(opts.verbose_name_raw)},
            )
            manager._add_to_cache(manager.db, ct)
            return ct

    def get_content_type(model, db=None):
        manager = ContentType.objects.db_manager(db)
        opts = model._meta
        if opts.proxy:
            return _get_for_proxy_model(manager, opts, model)
        else:
            return _get_for_concrete_model(manager, model)

    def get_content_types(models, db=None):
        manager = ContentType.objects.db_manager(db)
        content_types = {}
        concrete_models = []
        for model in models:
            opts = model._meta
            if opts.proxy:
                content_type = _get_for_proxy_model(manager, opts, model)
                content_types[model] = content_type
            else:
                concrete_models.append(model)
        content_types.update(_get_for_concrete_models(manager, concrete_models))
        return content_types

def copy_fields(src, to):
    """
    Returns a new instance of `to_cls` with fields data fetched from `src`.
    Useful for getting a model proxy instance from concrete model instance or
    the other way around. Note that we use *arg calling to get a faster model
    initialization.
    """
    args = tuple(getattr(src, field.attname) for field in src._meta.fields)
    return to(*args)

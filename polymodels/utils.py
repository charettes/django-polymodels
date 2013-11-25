from __future__ import unicode_literals

import sys

import django
from django.contrib.contenttypes.models import ContentType
try:
    from django.utils.encoding import smart_text
except ImportError:  # TODO: Remove when support for Django 1.4 is dropped
    from django.utils.encoding import smart_unicode as smart_text


# Prior to #18399 being fixed there was no way to retrieve `ContentType`
# of proxy models while caching it. This is a shim that tries to use the
# newly introduced flag and fallback to another method.
# TODO: Remove when support for Django 1.4 is dropped
if django.VERSION >= (1, 5):
    # django 1.5 introduced the `for_concrete_models?` kwarg
    def get_content_type(model, db=None):
        manager = ContentType.objects.db_manager(db)
        return manager.get_for_model(model, for_concrete_model=False)

    def get_content_types(models, db=None):
        manager = ContentType.objects.db_manager(db)
        return manager.get_for_models(*models, for_concrete_models=False)
else:
    def _get_for_proxy_model(manager, opts, model):
        if model._deferred:
            opts = opts.proxy_for_model._meta
        try:
            return manager._get_from_cache(opts)
        except KeyError:
            ct, _created = manager.get_or_create(
                app_label=opts.app_label,
                model=opts.object_name.lower(),
                defaults={'name': smart_text(opts.verbose_name_raw)},
            )
            manager._add_to_cache(manager.db, ct)
            return ct

    def get_content_type(model, db=None):
        manager = ContentType.objects.db_manager(db)
        opts = model._meta
        if opts.proxy:
            return _get_for_proxy_model(manager, opts, model)
        else:
            return manager.get_for_model(model)

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
        content_types.update(manager.get_for_models(*concrete_models))
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

# TODO: Remove when supports for Django 1.5 is dropped
if django.VERSION >= (1, 6):
    def get_queryset(manager, *args, **kwargs):
        return manager.get_queryset(*args, **kwargs)
else:
    def get_queryset(manager, *args, **kwargs):
        return manager.get_query_set(*args, **kwargs)


# TODO: Remove when support for Django 1.5 is dropped
if django.VERSION >= (1, 6):
    def model_name(opts):
        return opts.model_name
else:
    def model_name(opts):
        return opts.module_name


# TODO: replace uses by django.utils.six.string_types when support for Django 1.4 is dropped
string_types = str if sys.version_info[0] == 3 else basestring


def with_metaclass(meta, *bases):
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__

        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass(str('temporary_class'), None, {})

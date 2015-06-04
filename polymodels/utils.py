from __future__ import unicode_literals

from functools import partial

from django.contrib.contenttypes.models import ContentType


def copy_fields(src, to):
    """
    Returns a new instance of `to_cls` with fields data fetched from `src`.
    Useful for getting a model proxy instance from concrete model instance or
    the other way around. Note that we use *arg calling to get a faster model
    initialization.
    """
    args = tuple(getattr(src, field.attname) for field in src._meta.fields)
    return to(*args)


get_content_type = partial(ContentType.objects.get_for_model, for_concrete_model=False)
get_content_types = partial(ContentType.objects.get_for_models, for_concrete_models=False)

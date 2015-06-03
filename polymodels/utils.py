from __future__ import unicode_literals


def copy_fields(src, to):
    """
    Returns a new instance of `to_cls` with fields data fetched from `src`.
    Useful for getting a model proxy instance from concrete model instance or
    the other way around. Note that we use *arg calling to get a faster model
    initialization.
    """
    args = tuple(getattr(src, field.attname) for field in src._meta.fields)
    return to(*args)

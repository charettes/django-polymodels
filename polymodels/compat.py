from __future__ import unicode_literals

import django

# TODO: Remove the following when support for Django 1.8 is dropped
if django.VERSION >= (1, 9):
    def get_remote_field(field):
        return field.remote_field

    def get_remote_model(remote_field):
        return remote_field.model
else:
    def get_remote_field(field):
        return field.rel

    def get_remote_model(remote_field):
        return remote_field.to

try:
    from django.db.models.fields.related import lazy_related_operation
except ImportError:
    from django.db.models.fields.related import add_lazy_relation

    def lazy_related_operation(function, model, related_model, field):
        def operation(field, related, local):
            return function(local, related, field)
        add_lazy_relation(model, field, related_model, operation)

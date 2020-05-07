from __future__ import unicode_literals

from django import forms
from django.apps import apps
from django.core import checks
from django.db.models import ForeignKey, Q
from django.db.models.fields import NOT_PROVIDED
from django.db.models.fields.related import (
    RelatedField, lazy_related_operation,
)
from django.utils.deconstruct import deconstructible
from django.utils.functional import LazyObject, empty
from django.utils.translation import ugettext_lazy as _

from six import string_types

from .models import BasePolymorphicModel
from .utils import get_content_type


class LimitChoicesToSubclasses(object):
    def __init__(self, field, limit_choices_to):
        self.field = field
        self.limit_choices_to = limit_choices_to

    @property
    def value(self):
        subclasses_lookup = self.field.polymorphic_type.subclasses_lookup('pk')
        limit_choices_to = self.limit_choices_to
        if limit_choices_to is None:
            limit_choices_to = subclasses_lookup.copy()
        elif isinstance(limit_choices_to, dict):
            limit_choices_to = dict(limit_choices_to, **subclasses_lookup)
        elif isinstance(limit_choices_to, Q):
            limit_choices_to = limit_choices_to & Q(**subclasses_lookup)
        self.__dict__['value'] = limit_choices_to
        return limit_choices_to

    def __call__(self):
        return self.value


class LazyPolymorphicTypeQueryset(LazyObject):
    def __init__(self, remote_field, db):
        super(LazyPolymorphicTypeQueryset, self).__init__()
        self.__dict__.update(remote_field=remote_field, db=db)

    def _setup(self):
        remote_field = self.__dict__.get('remote_field')
        db = self.__dict__.get('db')
        self._wrapped = remote_field.model._default_manager.using(db).complex_filter(
            remote_field.limit_choices_to()
        )

    def __getattr__(self, attr):
        # ModelChoiceField._set_queryset(queryset) calls queryset.all() on
        # Django 2.1+ in order to clear possible cached results.
        # Since no results might have been cached before _setup() is called
        # it's safe to keep deferring until something else is accessed.
        if attr == 'all' and self._wrapped is empty:
            return lambda: self
        return super(LazyPolymorphicTypeQueryset, self).__getattr__(attr)


@deconstructible
class ContentTypeReference(object):
    def __init__(self, app_label, model_name):
        self.app_label = app_label
        self.model_name = model_name

    def __eq__(self, other):
        return isinstance(other, self.__class__) and (
            (self.app_label, self.model_name) == (other.app_label, other.model_name)
        )

    def __call__(self):
        model = apps.get_model(self.app_label, self.model_name)
        return get_content_type(model).pk

    def __repr__(self):
        return str("ContentTypeReference(%r, %r)" % (self.app_label, self.model_name))


class PolymorphicTypeField(ForeignKey):
    default_error_messages = {
        'invalid': _('Specified model is not a subclass of %(model)s.')
    }
    description = _(
        'Content type of a subclass of %(type)s'
    )
    default_kwargs = {
        'to': 'contenttypes.ContentType',
        'related_name': '+',
    }

    def __init__(self, polymorphic_type, *args, **kwargs):
        self.polymorphic_type = polymorphic_type
        self.overriden_default = False
        for kwarg, value in self.default_kwargs.items():
            kwargs.setdefault(kwarg, value)
        kwargs['limit_choices_to'] = LimitChoicesToSubclasses(self, kwargs.pop('limit_choices_to', None))
        super(PolymorphicTypeField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(PolymorphicTypeField, self).contribute_to_class(cls, name)
        polymorphic_type = self.polymorphic_type
        if (isinstance(polymorphic_type, string_types) or
                polymorphic_type._meta.pk is None):
            def resolve_polymorphic_type(model, related_model, field):
                field.do_polymorphic_type(related_model)
            lazy_related_operation(resolve_polymorphic_type, cls, polymorphic_type, field=self)
        else:
            self.do_polymorphic_type(polymorphic_type)

    def do_polymorphic_type(self, polymorphic_type):
        if self.default is NOT_PROVIDED and not self.null:
            opts = polymorphic_type._meta
            self.default = ContentTypeReference(opts.app_label, opts.model_name)
            self.overriden_default = True
        self.polymorphic_type = polymorphic_type
        self.type = polymorphic_type.__name__
        self.error_messages['invalid'] = (
            'Specified content type is not of a subclass of %s.' % polymorphic_type._meta.object_name
        )

    def check(self, **kwargs):
        errors = super(PolymorphicTypeField, self).check(**kwargs)
        if isinstance(self.polymorphic_type, string_types):
            errors.append(checks.Error(
                ("Field defines a relation with model '%s', which "
                 "is either not installed, or is abstract.") % self.polymorphic_type,
                id='fields.E300',
            ))
        elif not issubclass(self.polymorphic_type, BasePolymorphicModel):
            errors.append(checks.Error(
                "The %s type is not a subclass of BasePolymorphicModel." % self.polymorphic_type.__name__,
                id='polymodels.E004',
            ))
        return errors

    def formfield(self, **kwargs):
        db = kwargs.pop('using', None)
        if isinstance(self.polymorphic_type, string_types):
            raise ValueError(
                "Cannot create form field for %r yet, because its related model %r has not been loaded yet" % (
                    self.name, self.polymorphic_type
                )
            )
        defaults = {
            'form_class': forms.ModelChoiceField,
            'queryset': LazyPolymorphicTypeQueryset(self.remote_field, db),
            'to_field_name': self.remote_field.field_name,
        }
        defaults.update(kwargs)
        return super(RelatedField, self).formfield(**defaults)

    def deconstruct(self):
        name, path, args, kwargs = super(PolymorphicTypeField, self).deconstruct()
        opts = getattr(self.polymorphic_type, '_meta', None)
        kwargs['polymorphic_type'] = "%s.%s" % (opts.app_label, opts.object_name) if opts else self.polymorphic_type
        for kwarg, value in list(kwargs.items()):
            if self.default_kwargs.get(kwarg) == value:
                kwargs.pop(kwarg)
        if self.overriden_default:
            kwargs.pop('default')
        kwargs.pop('limit_choices_to', None)
        return name, path, args, kwargs

from __future__ import unicode_literals

from inspect import isclass

from django import forms
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey, Q
from django.db.models.fields import NOT_PROVIDED
from django.db.models.fields.related import RelatedField
from django.utils.deconstruct import deconstructible
from django.utils.functional import LazyObject
from django.utils.six import string_types
from django.utils.translation import ugettext_lazy as _

from .compat import get_remote_field, get_remote_model, lazy_related_operation
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
        self._wrapped = get_remote_model(remote_field)._default_manager.using(db).complex_filter(
            remote_field.limit_choices_to()
        )


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

    def __init__(self, polymorphic_type, *args, **kwargs):
        if not isinstance(polymorphic_type, string_types):
            self.validate_polymorphic_type(polymorphic_type)
        self.polymorphic_type = polymorphic_type
        limit_choices_to = LimitChoicesToSubclasses(self, kwargs.pop('limit_choices_to', None))
        defaults = {
            'to': ContentType,
            'related_name': '+',
            'limit_choices_to': limit_choices_to,
        }
        defaults.update(**kwargs)
        super(PolymorphicTypeField, self).__init__(*args, **defaults)

    def validate_polymorphic_type(self, model):
        if not isclass(model) or not issubclass(model, BasePolymorphicModel):
            raise AssertionError(
                "First parameter to `PolymorphicTypeField` must be "
                "a subclass of `BasePolymorphicModel`"
            )

    def contribute_to_class(self, cls, name):
        super(PolymorphicTypeField, self).contribute_to_class(cls, name)
        polymorphic_type = self.polymorphic_type
        if (isinstance(polymorphic_type, string_types) or
                polymorphic_type._meta.pk is None):
            def resolve_polymorphic_type(model, related_model, field):
                field.validate_polymorphic_type(related_model)
                field.do_polymorphic_type(related_model)
            lazy_related_operation(resolve_polymorphic_type, cls, polymorphic_type, field=self)
        else:
            self.do_polymorphic_type(polymorphic_type)

    def do_polymorphic_type(self, polymorphic_type):
        if self.default is NOT_PROVIDED and not self.null:
            opts = polymorphic_type._meta
            self.default = ContentTypeReference(opts.app_label, opts.model_name)
        self.polymorphic_type = polymorphic_type
        self.type = polymorphic_type.__name__
        self.error_messages['invalid'] = (
            'Specified content type is not of a subclass of %s.' % polymorphic_type._meta.object_name
        )

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
            'queryset': LazyPolymorphicTypeQueryset(get_remote_field(self), db),
            'to_field_name': get_remote_field(self).field_name,
        }
        defaults.update(kwargs)
        return super(RelatedField, self).formfield(**defaults)

    def deconstruct(self):
        name, _, args, kwargs = super(PolymorphicTypeField, self).deconstruct()
        path = 'django.db.models.fields.related.ForeignKey'
        return name, path, args, kwargs

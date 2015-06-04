from __future__ import unicode_literals

from django.forms import models
from django.utils.six import with_metaclass


class PolymorphicModelFormMetaclass(models.ModelFormMetaclass):
    def __new__(cls, name, bases, attrs):
        form = super(PolymorphicModelFormMetaclass, cls).__new__(
            cls, name, bases, attrs
        )
        model = form._meta.model
        form._meta.polymorphic_forms = {model: form}
        if model:
            for base in bases:
                for mro in base.__mro__:
                    if issubclass(mro, PolymorphicModelForm):
                        mro._meta.polymorphic_forms[model] = form
        return form

    def __getitem__(self, model):
        try:
            return self._meta.polymorphic_forms[model]
        except KeyError:
            raise TypeError("No form registered for %s." % model)


class PolymorphicModelForm(with_metaclass(PolymorphicModelFormMetaclass, models.ModelForm)):
    def __new__(cls, *args, **kwargs):
        instance = kwargs.get('instance', None)
        if instance:
            cls = cls[instance.__class__]
        return super(PolymorphicModelForm, cls).__new__(cls)

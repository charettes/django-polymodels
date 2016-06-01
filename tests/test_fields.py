from __future__ import unicode_literals

import django
from django.apps.registry import Apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.migrations.writer import MigrationWriter
from django.db.models.query_utils import Q

from polymodels.compat import get_remote_field
from polymodels.fields import ContentTypeReference, PolymorphicTypeField
from polymodels.models import PolymorphicModel
from polymodels.utils import get_content_type

from .base import TestCase
from .models import AcknowledgedTrait, HugeSnake, Snake, Trait


class ContentTypeReferenceTests(TestCase):
    reference = ContentTypeReference(str('polymodels'), str('snake'))

    def test_equality(self):
        self.assertEqual(self.reference, ContentTypeReference('polymodels', 'snake'))

    def test_retreival(self):
        self.assertEqual(self.reference(), get_content_type(Snake).pk)

    def test_repr(self):
        self.assertEqual(repr(self.reference), "ContentTypeReference('polymodels', 'snake')")


class PolymorphicTypeFieldTests(TestCase):
    def test_default_value(self):
        """
        Make sure fields defaults
        """
        trait = Trait.objects.create()
        self.assertIsNone(trait.trait_type)
        self.assertIsNone(trait.mammal_type)
        self.assertEqual(trait.snake_type.model_class(), Snake)

    def test_limit_choices_to(self):
        """
        Make sure existing `limit_choices_to` are taken into consideration
        """
        field = PolymorphicTypeField(Trait, on_delete=models.CASCADE)
        remote_field = get_remote_field(field)
        subclasses_lookup = Trait.subclasses_lookup('pk')
        self.assertEqual(remote_field.limit_choices_to(), subclasses_lookup)
        # Test dict() limit_choices_to.
        limit_choices_to = {'app_label': 'polymodels'}
        field = PolymorphicTypeField(Trait, on_delete=models.CASCADE, limit_choices_to=limit_choices_to)
        remote_field = get_remote_field(field)
        self.assertEqual(
            remote_field.limit_choices_to(), dict(subclasses_lookup, **limit_choices_to)
        )
        # Test Q() limit_choices_to.
        field = PolymorphicTypeField(Trait, on_delete=models.CASCADE, limit_choices_to=Q(**limit_choices_to))
        remote_field = get_remote_field(field)
        self.assertEqual(
            str(remote_field.limit_choices_to()), str(Q(**limit_choices_to) & Q(**subclasses_lookup))
        )

    def test_invalid_type(self):
        trait = Trait.objects.create()
        snake_type = get_content_type(Snake)
        trait.mammal_type = snake_type
        trait.snake_type = snake_type
        with self.assertRaisesMessage(
            ValidationError, 'Specified content type is not of a subclass of Mammal.'
        ):
            trait.full_clean()

    def test_valid_subclass(self):
        trait = Trait.objects.create()
        trait.snake_type = get_content_type(HugeSnake)
        trait.full_clean()

    def test_valid_proxy_subclass(self):
        trait = Trait.objects.create()
        trait.trait_type = get_content_type(AcknowledgedTrait)
        trait.full_clean()

    def test_description(self):
        trait_type = Trait._meta.get_field('trait_type')
        self.assertEqual(
            trait_type.description % trait_type.__dict__,
            'Content type of a subclass of Trait'
        )

    def test_invalid_polymorphic_model(self):
        with self.assertRaisesMessage(
            AssertionError, "First parameter to `PolymorphicTypeField` must be a subclass of `BasePolymorphicModel`"
        ):
            PolymorphicTypeField(None)
        with self.assertRaisesMessage(
            AssertionError, "First parameter to `PolymorphicTypeField` must be a subclass of `BasePolymorphicModel`"
        ):
            PolymorphicTypeField(models.Model)

    def test_formfield_issues_no_queries(self):
        trait_type = Trait._meta.get_field('trait_type')
        with self.assertNumQueries(0):
            formfield = trait_type.formfield()
        self.assertSetEqual(set(formfield.queryset), {
            get_content_type(Trait),
            get_content_type(AcknowledgedTrait),
        })

    def test_unresolved_relationship_formfield(self):
        field = PolymorphicTypeField('Snake', to='app.Unresolved', on_delete=models.CASCADE)
        with self.assertRaises(ValueError):
            field.formfield()

    def safe_exec(self, string, value=None):
        l = {}
        try:
            exec(string, globals(), l)
        except Exception as e:
            if value:
                self.fail("Could not exec %r (from value %r): %s" % (string.strip(), value, e))
            else:
                self.fail("Could not exec %r: %s" % (string.strip(), e))
        return l

    def serialize_round_trip(self, value):
        string, imports = MigrationWriter.serialize(value)
        return self.safe_exec("%s\ntest_value_result = %s" % ("\n".join(imports), string), value)['test_value_result']

    def assertDeconstructionEqual(self, field, deconstructed):
        self.assertEqual(field.deconstruct(), deconstructed)
        self.assertEqual(self.serialize_round_trip(deconstructed), deconstructed)

    def test_field_deconstruction(self):
        test_apps = Apps()

        class Foo(PolymorphicModel):
            foo = PolymorphicTypeField('self', on_delete=models.CASCADE)

            class Meta:
                apps = test_apps
                app_label = 'polymodels'

        class Bar(models.Model):
            foo = PolymorphicTypeField('Foo', on_delete=models.CASCADE)
            foo_null = PolymorphicTypeField(Foo, on_delete=models.CASCADE, null=True)
            foo_default = PolymorphicTypeField(Foo, on_delete=models.CASCADE, default=get_content_type(Foo).pk)

            class Meta:
                apps = test_apps
                app_label = 'polymodels'

        def django_version_agnostic(deconstruction):
            # As of Django 1.9+ on_delete is a required parameter and
            # doesn't default to models.CASCADE anymore.
            if django.VERSION >= (1, 9):
                deconstruction['on_delete'] = models.CASCADE
            return deconstruction

        self.assertDeconstructionEqual(Foo._meta.get_field('foo'), (
            'foo', 'django.db.models.fields.related.ForeignKey', [], django_version_agnostic({
                'to': 'contenttypes.ContentType',
                'related_name': '+',
                'default': ContentTypeReference('polymodels', 'foo'),
            })
        ))
        self.assertDeconstructionEqual(Bar._meta.get_field('foo'), (
            'foo', 'django.db.models.fields.related.ForeignKey', [], django_version_agnostic({
                'to': 'contenttypes.ContentType',
                'related_name': '+',
                'default': ContentTypeReference('polymodels', 'foo'),
            })
        ))
        self.assertDeconstructionEqual(Bar._meta.get_field('foo_null'), (
            'foo_null', 'django.db.models.fields.related.ForeignKey', [], django_version_agnostic({
                'to': 'contenttypes.ContentType',
                'related_name': '+',
                'null': True,
            })
        ))
        self.assertDeconstructionEqual(Bar._meta.get_field('foo_default'), (
            'foo_default', 'django.db.models.fields.related.ForeignKey', [], django_version_agnostic({
                'to': 'contenttypes.ContentType',
                'related_name': '+',
                'default': get_content_type(Foo).pk,
            })
        ))

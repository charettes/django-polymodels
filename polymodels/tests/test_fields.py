from __future__ import unicode_literals

import django
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query_utils import Q

from ..compat import get_content_type, get_remote_field, skipUnless
from ..fields import PolymorphicTypeField

from .base import TestCase
from .models import AcknowledgedTrait, HugeSnake, Snake, Trait


try:
    import south
except ImportError:
    south = None


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
        trait_type = Trait._meta.get_field('trait_type')

        # Make sure it's cached
        limit_choices_to = get_remote_field(trait_type).limit_choices_to
        self.assertIn('limit_choices_to', get_remote_field(trait_type).__dict__)

        extra_limit_choices_to = {'app_label': 'polymodels'}

        # Make sure it works with existing dict `limit_choices_to`
        get_remote_field(trait_type).limit_choices_to = extra_limit_choices_to
        # Cache should be cleared
        self.assertNotIn('limit_choices_to', get_remote_field(trait_type).__dict__)
        self.assertEqual(
            get_remote_field(trait_type).limit_choices_to,
            dict(extra_limit_choices_to, **limit_choices_to)
        )

        # Make sure it works with existing Q `limit_choices_to`
        get_remote_field(trait_type).limit_choices_to = Q(**extra_limit_choices_to)
        # Cache should be cleared
        self.assertNotIn('limit_choices_to', get_remote_field(trait_type).__dict__)
        self.assertEqual(
            str(get_remote_field(trait_type).limit_choices_to),
            str(Q(**extra_limit_choices_to) & Q(**limit_choices_to))
        )

        # Re-assign the original value
        get_remote_field(trait_type).limit_choices_to = None
        # Cache should be cleared
        self.assertNotIn('limit_choices_to', get_remote_field(trait_type).__dict__)

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
        self.assertSetEqual(set(formfield.queryset), set([
            get_content_type(Trait),
            get_content_type(AcknowledgedTrait)
        ]))

    def test_unresolved_relationship_formfield(self):
        field = PolymorphicTypeField('Snake', to='app.Unresolved')
        with self.assertRaises(ValueError):
            field.formfield()

    @skipUnless(south, 'South is not installed.')
    def test_south_field_triple(self):
        field = PolymorphicTypeField('Snake')
        self.assertEqual(field.south_field_triple(), (
            'django.db.models.fields.related.ForeignKey', [], {
                'related_name': repr('+'),
                'to': "orm['contenttypes.ContentType']"
            }
        ))
        field = PolymorphicTypeField('Snake', null=True)
        self.assertEqual(field.south_field_triple(), (
            'django.db.models.fields.related.ForeignKey', [], {
                'related_name': repr('+'),
                'to': "orm['contenttypes.ContentType']",
                'null': repr(True)
            }
        ))

    @skipUnless(django.VERSION >= (1, 7),
                'Field deconstruction is only supported on Django 1.7+')
    def test_field_deconstruction(self):
        field = PolymorphicTypeField('Snake')
        self.assertEqual(field.deconstruct(), (
            None, 'django.db.models.fields.related.ForeignKey', [], {
                'to': 'contenttypes.ContentType',
                'related_name': '+',
            }
        ))
        field = PolymorphicTypeField('Snake', null=True)
        self.assertEqual(field.deconstruct(), (
            None, 'django.db.models.fields.related.ForeignKey', [], {
                'to': 'contenttypes.ContentType',
                'null': True,
                'related_name': '+',
            }
        ))

from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query_utils import Q

from polymodels.compat import get_remote_field
from polymodels.fields import PolymorphicTypeField
from polymodels.utils import get_content_type

from .base import TestCase
from .models import AcknowledgedTrait, HugeSnake, Snake, Trait


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
        type_field = Trait._meta.get_field('trait_type')
        remote_field = get_remote_field(type_field)

        # Make sure it's cached
        limit_choices_to = remote_field.limit_choices_to
        self.assertIn('limit_choices_to', remote_field.__dict__)

        extra_limit_choices_to = {'app_label': 'polymodels'}

        # Make sure it works with existing dict `limit_choices_to`
        remote_field.limit_choices_to = extra_limit_choices_to
        # Cache should be cleared
        self.assertNotIn('limit_choices_to', remote_field.__dict__)
        self.assertEqual(
            remote_field.limit_choices_to,
            dict(extra_limit_choices_to, **limit_choices_to)
        )

        # Make sure it works with existing Q `limit_choices_to`
        remote_field.limit_choices_to = Q(**extra_limit_choices_to)
        # Cache should be cleared
        self.assertNotIn('limit_choices_to', remote_field.__dict__)
        remote_field_limit_choices_to = remote_field.limit_choices_to
        self.assertEqual(remote_field_limit_choices_to.connector, Q.AND)
        self.assertFalse(remote_field_limit_choices_to.negated)
        self.assertEqual(
            remote_field_limit_choices_to.children,
            list(extra_limit_choices_to.items()) + list(limit_choices_to.items())
        )

        # Re-assign the original value
        remote_field.limit_choices_to = None
        # Cache should be cleared
        self.assertNotIn('limit_choices_to', remote_field.__dict__)

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
        field = PolymorphicTypeField('Snake', to='app.Unresolved')
        with self.assertRaises(ValueError):
            field.formfield()

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

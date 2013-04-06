from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from ..models import BasePolymorphicModel

from .base import TestCase
from .models import Animal, BigSnake, HugeSnake, Mammal, Snake


class BasePolymorphicModelTest(TestCase):
    def test_improperly_configured(self):
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`BasePolymorphicModel` subclasses must '
                                       'define a `CONTENT_TYPE_FIELD`.'):
            class NoCtFieldModel(BasePolymorphicModel):
                pass
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`polymodels.tests.test_models.InexistentCtFieldModel.CONTENT_TYPE_FIELD` '
                                      'points to an inexistent field "inexistent_field".'):
            class InexistentCtFieldModel(BasePolymorphicModel):
                CONTENT_TYPE_FIELD = 'inexistent_field'
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`polymodels.tests.test_models.InvalidCtFieldModel.a_char_field` '
                                      'must be a `ForeignKey` to `ContentType`.'):
            class InvalidCtFieldModel(BasePolymorphicModel):
                CONTENT_TYPE_FIELD = 'a_char_field'
                a_char_field = models.CharField(max_length=255)
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`polymodels.tests.test_models.InvalidCtFkFieldToModel.a_fk` '
                                      'must be a `ForeignKey` to `ContentType`.'):
            class InvalidCtFkFieldToModel(BasePolymorphicModel):
                CONTENT_TYPE_FIELD = 'a_fk'
                a_fk = models.ForeignKey('self')

    def test_type_cast(self):
        animal_dog = Animal.objects.create(name='dog')
        self.assertEqual(animal_dog.type_cast(), animal_dog,
                         'Type casting a correctly typed class should work.')
        mammal_cat = Mammal.objects.create(name='cat')
        self.assertEqual(mammal_cat.type_cast(), mammal_cat,
                         'Type casting a correctly typed subclass should work.')
        animal_cat = Animal.objects.get(pk=mammal_cat.pk)
        self.assertEqual(animal_cat.type_cast(), mammal_cat)
        try:
            animal_dog.type_cast(Mammal)
        except Mammal.DoesNotExist:
            pass
        else:
            self.fail('When trying to type cast to an inexistent model an '
                      'exception should be raised.')
        self.assertRaises(Mammal.DoesNotExist, animal_dog.type_cast, Mammal)
        # That's a big snake
        anaconda_snake = Snake.objects.create(name='anaconda', length=152)
        anaconda_big_snake = anaconda_snake.type_cast(BigSnake)
        self.assertIsInstance(anaconda_big_snake, BigSnake,
                              'Proxy type casting should work')
        self.assertIsInstance(anaconda_snake.type_cast(HugeSnake), HugeSnake,
                              'Two level proxy type casting should work')

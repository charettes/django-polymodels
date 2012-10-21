import re

import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test.testcases import TestCase

from polymodels.managers import PolymorphicManager
from polymodels.models import BasePolymorphicModel, PolymorphicModel
from polymodels.utils import get_content_types


class Animal(PolymorphicModel):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)

    def __unicode__(self):
        return self.name


class Mammal(Animal):
    pass


class Monkey(Mammal):
    pass


class Reptile(Animal):
    length = models.SmallIntegerField()

    class Meta:
        abstract = True


class Snake(Reptile):
    pass


class BigSnake(Snake):
    class Meta:
        proxy = True


class HugeSnake(BigSnake):
    class Meta:
        proxy = True


# TODO: Remove when support for django 1.3 is dropped
if django.VERSION < (1, 4):
    class TestCase(TestCase):
        def assertRaisesMessage(self, expected_exception, expected_message,
                                callable_obj=None, *args, **kwargs):
            return self.assertRaisesRegexp(expected_exception,
                    re.escape(expected_message), callable_obj, *args, **kwargs)


class PolymorphicQuerySetTest(TestCase):
    def test_select_subclasses(self):
        Animal.objects.create(name='animal')
        Mammal.objects.create(name='mammal')
        Monkey.objects.create(name='monkey')
        Snake.objects.create(name='snake', length=10)
        BigSnake.objects.create(name='big snake', length=101)
        HugeSnake.objects.create(name='huge snake', length=155)
        # Get content types to avoid query count pollution
        get_content_types((Animal, Mammal, Snake, BigSnake, HugeSnake))
        # One extra for the Monkey until django #16572 is fixed
        with self.assertNumQueries(2):
            self.assertQuerysetEqual(Animal.objects.select_subclasses(),
                                     ['<Animal: animal>',
                                      '<Mammal: mammal>',
                                      '<Monkey: monkey>',
                                      '<Snake: snake>',
                                      '<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])
        # One extra for the Monkey until django #16572 is fixed
        with self.assertNumQueries(2):
            self.assertQuerysetEqual(Animal.objects.select_subclasses(Mammal),
                                     ['<Mammal: mammal>',
                                      '<Monkey: monkey>'])
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(Animal.objects.select_subclasses(Snake),
                                     ['<Snake: snake>',
                                      '<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(Snake.objects.select_subclasses(),
                                     ['<Snake: snake>',
                                      '<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(Snake.objects.select_subclasses(BigSnake),
                                     ['<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])

    def test_exclude_subclasses(self):
        Animal.objects.create(name='animal')
        Mammal.objects.create(name='first mammal')
        Mammal.objects.create(name='second mammal')
        Monkey.objects.create(name='donkey kong')
        self.assertQuerysetEqual(Animal.objects.exclude_subclasses(),
                                 ['<Animal: animal>',])
        self.assertQuerysetEqual(Mammal.objects.exclude_subclasses(),
                                 ['<Mammal: first mammal>',
                                  '<Mammal: second mammal>'])
        self.assertQuerysetEqual(Monkey.objects.exclude_subclasses(),
                                 ['<Monkey: donkey kong>',])



class PolymorphicManagerTest(TestCase):
    def test_improperly_configured(self):
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`PolymorphicManager` can only be used '
                                       'on `BasePolymorphicModel` subclasses.'):
            class NonPolymorphicModel(models.Model):
                objects = PolymorphicManager()


class BasePolymorphicModelTest(TestCase):
    def test_improperly_configured(self):
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`BasePolymorphicModel` subclasses must '
                                       'define a `CONTENT_TYPE_FIELD`.'):
            class NoCtFieldModel(BasePolymorphicModel):
                pass
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`polymodels.tests.InexistentCtFieldModel.CONTENT_TYPE_FIELD` '
                                      'points to an inexistent field "inexistent_field".'):
            class InexistentCtFieldModel(BasePolymorphicModel):
                CONTENT_TYPE_FIELD = 'inexistent_field'
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`polymodels.tests.InvalidCtFieldModel.a_char_field` '
                                      'must be a `ForeignKey` to `ContentType`.'):
            class InvalidCtFieldModel(BasePolymorphicModel):
                CONTENT_TYPE_FIELD = 'a_char_field'
                a_char_field = models.CharField(max_length=255)
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`polymodels.tests.InvalidCtFkFieldToModel.a_fk` '
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

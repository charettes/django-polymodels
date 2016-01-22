from __future__ import unicode_literals

from django.apps.registry import Apps
from django.core import checks
from django.db import models
from django.test.testcases import SimpleTestCase

from polymodels.models import (
    EMPTY_ACCESSOR, BasePolymorphicModel, SubclassAccessors,
)

from .base import TestCase
from .models import Animal, BigSnake, HugeSnake, Mammal, Snake


class BasePolymorphicModelTest(TestCase):
    def test_checks(self):
        test_apps = Apps()
        options = type(str('Meta'), (), {'apps': test_apps, 'app_label': 'polymodels'})

        class NoCtFieldModel(BasePolymorphicModel):
            Meta = options

        self.assertIn(checks.Error(
            '`BasePolymorphicModel` subclasses must define a `CONTENT_TYPE_FIELD`.',
            hint=None,
            obj=NoCtFieldModel,
            id='polymodels.E001',
        ), NoCtFieldModel.check())

        class InexistentCtFieldModel(BasePolymorphicModel):
            CONTENT_TYPE_FIELD = 'inexistent_field'

            Meta = options

        self.assertIn(checks.Error(
            "`CONTENT_TYPE_FIELD` points to an inexistent field 'inexistent_field'.",
            hint=None,
            obj=InexistentCtFieldModel,
            id='polymodels.E002',
        ), InexistentCtFieldModel.check())

        class InvalidCtFieldModel(BasePolymorphicModel):
            CONTENT_TYPE_FIELD = 'a_char_field'
            a_char_field = models.CharField(max_length=255)

            Meta = options

        self.assertIn(checks.Error(
            "`a_char_field` must be a `ForeignKey` to `ContentType`.",
            hint=None,
            obj=InvalidCtFieldModel._meta.get_field('a_char_field'),
            id='polymodels.E003',
        ), InvalidCtFieldModel.check())

        class InvalidCtFkFieldToModel(BasePolymorphicModel):
            CONTENT_TYPE_FIELD = 'a_fk'
            a_fk = models.ForeignKey('self', on_delete=models.CASCADE)

            Meta = options

        self.assertIn(checks.Error(
            "`a_fk` must be a `ForeignKey` to `ContentType`.",
            hint=None,
            obj=InvalidCtFkFieldToModel._meta.get_field('a_fk'),
            id='polymodels.E003',
        ), InvalidCtFkFieldToModel.check())

    def test_type_cast(self):
        animal_dog = Animal.objects.create(name='dog')
        with self.assertNumQueries(0):
            self.assertEqual(
                animal_dog.type_cast(), animal_dog,
                'Type casting a correctly typed class should work.'
            )

        mammal_cat = Mammal.objects.create(name='cat')
        with self.assertNumQueries(0):
            self.assertEqual(
                mammal_cat.type_cast(), mammal_cat,
                'Type casting a correctly typed subclass should work.'
            )

        animal_cat = Animal.objects.get(pk=mammal_cat.pk)
        with self.assertNumQueries(1):
            self.assertEqual(animal_cat.type_cast(), mammal_cat)

        # When trying to type cast to an inexistent model an exception
        # should be raised.'
        with self.assertRaises(Mammal.DoesNotExist):
            animal_dog.type_cast(Mammal)

        # That's a big snake
        anaconda_snake = Snake.objects.create(name='anaconda', length=152)

        with self.assertNumQueries(0):
            self.assertIsInstance(
                anaconda_snake.type_cast(BigSnake), BigSnake,
                'Proxy type casting should work'
            )

        with self.assertNumQueries(0):
            self.assertIsInstance(
                anaconda_snake.type_cast(HugeSnake), HugeSnake,
                'Two level proxy type casting should work'
            )

    def test_type_cast_on_child_class(self):
        mammal = Mammal.objects.create()
        snake = Snake.objects.create(length=1)

        self.assertEqual(mammal.type_cast(), mammal)
        self.assertEqual(snake.animal_ptr.type_cast(), snake)


class SubclassAccessorsTests(SimpleTestCase):
    def test_dynamic_model_creation_cache_busting(self):
        test_apps = Apps(['tests'])

        class Base(models.Model):
            class Meta:
                apps = test_apps

            accessors = SubclassAccessors()

        self.assertEqual(Base.accessors, {Base: EMPTY_ACCESSOR})

        class DynamicChild(Base):
            class Meta:
                apps = test_apps

        self.assertEqual(Base.accessors, {
            Base: EMPTY_ACCESSOR,
            DynamicChild: (('dynamicchild',), None, 'dynamicchild'),
        })

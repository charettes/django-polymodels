from __future__ import unicode_literals

from django.apps.registry import Apps
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models
from django.test.testcases import SimpleTestCase

from polymodels.models import (
    EMPTY_ACCESSOR, BasePolymorphicModel, SubclassAccessor, SubclassAccessors,
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
        anaconda_snake = Snake.objects.create(name='anaconda', length=152, color='green')

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

        for subclass in [Snake, BigSnake, HugeSnake]:
            anaconda_animal = Animal.objects.get(pk=anaconda_snake.pk)
            with self.assertNumQueries(1):
                anaconda_animal_type_casted = anaconda_animal.type_cast(subclass)
            self.assertIsInstance(anaconda_animal_type_casted, subclass)
            self.assertEqual(anaconda_animal_type_casted.color, 'green')

    def test_content_type_saving(self):
        # Creating a base class should assign the correct content_type.
        animal_content_type = ContentType.objects.get_for_model(Animal)
        with self.assertNumQueries(1):
            animal = Animal.objects.create(name='dog')
        self.assertEqual(animal.content_type, animal_content_type)

        # Creating subclass should assign the correct content_type.
        mammal_content_type = ContentType.objects.get_for_model(Mammal)
        with self.assertNumQueries(2):
            mammal = Mammal.objects.create(name='cat')
        self.assertEqual(mammal.content_type, mammal_content_type)

        # Updating a subclass's base class pointer should preserve content_type.
        mammal.animal_ptr.save()
        self.assertEqual(mammal.animal_ptr.content_type, mammal_content_type)
        self.assertEqual(mammal.content_type, mammal_content_type)

        # Creating a base class should honor explicit content_type.
        with self.assertNumQueries(1):
            explicit_mammal = Animal.objects.create(name='beaver', content_type=mammal_content_type)
        self.assertEqual(explicit_mammal.content_type, mammal_content_type)
        with self.assertNumQueries(2):
            beaver = Mammal.objects.create(animal_ptr=explicit_mammal)
        self.assertEqual(explicit_mammal.content_type, mammal_content_type)
        self.assertEqual(beaver.content_type, mammal_content_type)

    def test_delete_keep_parents(self):
        snake = HugeSnake.objects.create(name='snek', length=30)
        animal_pk = snake.pk
        animal_content_type = ContentType.objects.get_for_model(Animal)

        snake.delete(keep_parents=True)
        animal = Animal.objects.get(pk=animal_pk)
        self.assertEqual(animal.content_type, animal_content_type)


class SubclassAccessorsTests(SimpleTestCase):
    def test_dynamic_model_creation_cache_busting(self):
        test_apps = Apps(['tests'])

        class Base(models.Model):
            class Meta:
                apps = test_apps

            accessors = SubclassAccessors()

        self.assertEqual(Base.accessors['tests', 'base'], {Base: EMPTY_ACCESSOR})

        class DynamicChild(Base):
            class Meta:
                apps = test_apps

        self.assertEqual(Base.accessors['tests', 'base'], {
            Base: EMPTY_ACCESSOR,
            DynamicChild: (('dynamicchild',), None, 'dynamicchild'),
        })

        self.assertEqual(DynamicChild.accessors, {
            DynamicChild: EMPTY_ACCESSOR,
        })

    def test_key_error(self):
        test_apps = Apps(['tests'])

        class Base(models.Model):
            class Meta:
                apps = test_apps

            accessors = SubclassAccessors()

        class Other(models.Model):
            class Meta:
                apps = test_apps

        with self.assertRaises(KeyError):
            Base.accessors['tests', 'other']

    def test_proxy_accessors(self):
        test_apps = Apps(['tests'])

        class Base(models.Model):
            class Meta:
                apps = test_apps
                abstract = True

            accessors = SubclassAccessors()

        class Polymorphic(Base):
            class Meta:
                apps = test_apps
                abstract = True

        class Root(Polymorphic):
            class Meta:
                apps = test_apps

        class Subclass(Root):
            class Meta:
                apps = test_apps

        class SubclassProxy(Subclass):
            class Meta:
                apps = test_apps
                proxy = True

        class SubclassProxyProxy(SubclassProxy):
            class Meta:
                apps = test_apps
                proxy = True

        self.assertEqual(Root.accessors[Subclass], SubclassAccessor(('subclass',), None, 'subclass'))
        self.assertEqual(Root.accessors[SubclassProxy], SubclassAccessor(('subclass',), SubclassProxy, 'subclass'))
        self.assertEqual(
            Root.accessors[SubclassProxyProxy],
            SubclassAccessor(('subclass',), SubclassProxyProxy, 'subclass')
        )
        self.assertEqual(Subclass.accessors[SubclassProxy], SubclassAccessor((), SubclassProxy, ''))
        self.assertEqual(Subclass.accessors[SubclassProxyProxy], SubclassAccessor((), SubclassProxyProxy, ''))
        self.assertEqual(SubclassProxy.accessors[SubclassProxyProxy], SubclassAccessor((), SubclassProxyProxy, ''))

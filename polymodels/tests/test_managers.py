from __future__ import unicode_literals

import django
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from ..managers import PolymorphicManager

from .base import TestCase
from .models import Animal, BigSnake, HugeSnake, Mammal, Monkey, Snake


class PolymorphicQuerySetTest(TestCase):
    def test_select_subclasses(self):
        Animal.objects.create(name='animal')
        Mammal.objects.create(name='mammal')
        Monkey.objects.create(name='monkey')
        Snake.objects.create(name='snake', length=10)
        BigSnake.objects.create(name='big snake', length=101)
        HugeSnake.objects.create(name='huge snake', length=155)
        # Assert `select_subclasses` correctly calls `select_related` and `filter`.
        animals = Animal.objects.select_subclasses()
        animals_expected_num_queries = 1
        animals_expected_query_select_related = {
            'mammal': {'monkey': {}},
            'snake': {},
            'content_type': {}
        }
        # We can't do `select_related` on multiple one-to-one
        # relationships on django < 1.6, thus it generates extra queries
        if django.VERSION < (1, 6):
            animals_expected_num_queries += Monkey.objects.count()
            animals_expected_query_select_related['mammal'] = {}
        self.assertEqual(animals.query.select_related, animals_expected_query_select_related)
        with self.assertNumQueries(animals_expected_num_queries):
            self.assertQuerysetEqual(animals.all(),
                                     ['<Animal: animal>',
                                      '<Mammal: mammal>',
                                      '<Monkey: monkey>',
                                      '<Snake: snake>',
                                      '<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])
        # Filter out non-mammal (direct subclass)
        animal_mammals = Animal.objects.select_subclasses(Mammal)
        animal_mammals_expected_num_queries = 1
        animal_mammals_expected_query_select_related = {
            'mammal': {'monkey': {}},
            'content_type': {}
        }
        # We can't do `select_related` on multiple one-to-one
        # relationships on django < 1.6, thus it generates extra queries
        if django.VERSION < (1, 6):
            animal_mammals_expected_num_queries += Monkey.objects.count()
            animal_mammals_expected_query_select_related['mammal'] = {}
        self.assertEqual(
            animal_mammals.query.select_related,
            animal_mammals_expected_query_select_related
        )
        with self.assertNumQueries(animal_mammals_expected_num_queries):
            self.assertQuerysetEqual(animal_mammals.all(),
                                     ['<Mammal: mammal>',
                                      '<Monkey: monkey>'])
        # Filter out non-snake (subclass through an abstract one)
        animal_snakes = Animal.objects.select_subclasses(Snake)
        self.assertEqual(animal_snakes.query.select_related, {
            'snake': {},
            'content_type': {}
        })
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(animal_snakes.all(),
                                     ['<Snake: snake>',
                                      '<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])
        # Subclass with only proxies
        snakes = Snake.objects.select_subclasses()
        self.assertEqual(snakes.query.select_related, {
            'content_type': {}
        })
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(snakes.all(),
                                     ['<Snake: snake>',
                                      '<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])
        # Subclass filter proxies
        snake_bigsnakes = Snake.objects.select_subclasses(BigSnake)
        self.assertEqual(snake_bigsnakes.query.select_related, {
            'content_type': {}
        })
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(snake_bigsnakes.all(),
                                     ['<BigSnake: big snake>',
                                      '<HugeSnake: huge snake>'])

    def test_exclude_subclasses(self):
        Animal.objects.create(name='animal')
        Mammal.objects.create(name='first mammal')
        Mammal.objects.create(name='second mammal')
        Monkey.objects.create(name='donkey kong')
        self.assertQuerysetEqual(Animal.objects.exclude_subclasses(),
                                 ['<Animal: animal>'])
        self.assertQuerysetEqual(Mammal.objects.exclude_subclasses(),
                                 ['<Mammal: first mammal>',
                                  '<Mammal: second mammal>'])
        self.assertQuerysetEqual(Monkey.objects.exclude_subclasses(),
                                 ['<Monkey: donkey kong>'])


class PolymorphicManagerTest(TestCase):
    def test_improperly_configured(self):
        with self.assertRaisesMessage(ImproperlyConfigured,
                                      '`PolymorphicManager` can only be used '
                                       'on `BasePolymorphicModel` subclasses.'):
            class NonPolymorphicModel(models.Model):
                objects = PolymorphicManager()

from __future__ import unicode_literals
import sys

from django.db import models

from ..models import PolymorphicModel


class Zoo(models.Model):
    animals = models.ManyToManyField('Animal')

    class Meta:
        app_label = 'polymodels'


class Animal(PolymorphicModel):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'polymodels'
        ordering = ('id',)

    def __str__(self):
        return self.name

    if not sys.version_info[0] == 3:
        __unicode__ = __str__
        __str__ = lambda self: self.__unicode__().encode('utf-8')


class Mammal(Animal):
    class Meta:
        app_label = 'polymodels'


class Monkey(Mammal):
    class Meta:
        app_label = 'polymodels'


class Reptile(Animal):
    length = models.SmallIntegerField()

    class Meta:
        app_label = 'polymodels'
        abstract = True
        ordering = ('id',)


class Snake(Reptile):
    class Meta:
        app_label = 'polymodels'
        ordering = ('id',)


class BigSnake(Snake):
    class Meta:
        app_label = 'polymodels'
        proxy = True


class HugeSnake(BigSnake):
    class Meta:
        app_label = 'polymodels'
        proxy = True

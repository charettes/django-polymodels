from __future__ import unicode_literals

import sys

from django.db import models

from ..fields import PolymorphicTypeField
from ..models import PolymorphicModel


class Zoo(models.Model):
    animals = models.ManyToManyField('Animal')

    class Meta:
        app_label = 'polymodels'


class Animal(PolymorphicModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = 'polymodels'
        ordering = ['id']

    def __str__(self):
        return self.name

    if not sys.version_info[0] == 3:
        __unicode__ = __str__

        def __str__(self):
            return self.__unicode__().encode('utf-8')


class Mammal(Animal):
    class Meta:
        app_label = 'polymodels'


class Monkey(Mammal):
    class Meta:
        app_label = 'polymodels'


class Trait(PolymorphicModel):
    trait_type = PolymorphicTypeField('self', blank=True, null=True)
    mammal_type = PolymorphicTypeField(Mammal, blank=True, null=True)
    snake_type = PolymorphicTypeField('Snake')

    class Meta:
        app_label = 'polymodels'


class AcknowledgedTrait(Trait):
    class Meta:
        app_label = 'polymodels'
        proxy = True


class Reptile(Animal):
    length = models.SmallIntegerField()

    class Meta:
        app_label = 'polymodels'
        abstract = True
        ordering = ['id']


class Snake(Reptile):
    class Meta:
        app_label = 'polymodels'
        ordering = ['id']


class BigSnake(Snake):
    class Meta:
        app_label = 'polymodels'
        proxy = True


class HugeSnake(BigSnake):
    class Meta:
        app_label = 'polymodels'
        proxy = True

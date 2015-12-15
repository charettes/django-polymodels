from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from polymodels.fields import PolymorphicTypeField
from polymodels.models import PolymorphicModel


class Zoo(models.Model):
    animals = models.ManyToManyField('Animal')

    class Meta:
        app_label = 'polymodels'


@python_2_unicode_compatible
class Animal(PolymorphicModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = 'polymodels'
        ordering = ['id']

    def __str__(self):
        return self.name


class NotInstalledAnimal(Animal):
    class Meta:
        app_label = 'not_installed'


class Mammal(Animal):
    class Meta:
        app_label = 'polymodels'


class Monkey(Mammal):
    class Meta:
        app_label = 'polymodels'


class Trait(PolymorphicModel):
    trait_type = PolymorphicTypeField('self', on_delete=models.CASCADE, blank=True, null=True)
    mammal_type = PolymorphicTypeField(Mammal, on_delete=models.CASCADE, blank=True, null=True)
    snake_type = PolymorphicTypeField('Snake', on_delete=models.CASCADE)

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

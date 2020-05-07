from __future__ import unicode_literals

from django.db import models

from polymodels.fields import PolymorphicTypeField
from polymodels.models import PolymorphicModel

try:
    from django.utils.encoding import python_2_unicode_compatible
except ImportError:
    def python_2_unicode_compatible(cls):
        return cls


class Zoo(models.Model):
    animals = models.ManyToManyField('Animal', related_name='zoos')


@python_2_unicode_compatible
class Animal(PolymorphicModel):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class NotInstalledAnimal(Animal):
    class Meta:
        app_label = 'not_installed'


class Mammal(Animal):
    pass


class Monkey(Mammal):
    friends = models.ManyToManyField('self')


class Trait(PolymorphicModel):
    trait_type = PolymorphicTypeField('self', on_delete=models.CASCADE, blank=True, null=True)
    mammal_type = PolymorphicTypeField(Mammal, on_delete=models.CASCADE, blank=True, null=True)
    snake_type = PolymorphicTypeField('Snake', on_delete=models.CASCADE)


class AcknowledgedTrait(Trait):
    class Meta:
        proxy = True


class Reptile(Animal):
    length = models.SmallIntegerField()

    class Meta:
        abstract = True
        ordering = ['id']


class Snake(Reptile):
    color = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['id']


class BigSnake(Snake):
    class Meta:
        proxy = True


class HugeSnake(BigSnake):
    class Meta:
        proxy = True

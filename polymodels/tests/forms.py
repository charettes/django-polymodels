from __future__ import unicode_literals

from ..forms import PolymorphicModelForm

from .models import Animal, BigSnake, Snake


class AnimalForm(PolymorphicModelForm):
    class Meta:
        fields = ['name']
        model = Animal


class SnakeForm(AnimalForm):
    class Meta:
        model = Snake


class BigSnakeForm(SnakeForm):
    class Meta:
        model = BigSnake

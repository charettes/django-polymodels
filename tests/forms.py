from polymodels.forms import PolymorphicModelForm

from .models import Animal, BigSnake, Snake


class AnimalForm(PolymorphicModelForm):
    class Meta:
        fields = ["name"]
        model = Animal


class SnakeForm(AnimalForm):
    class Meta:
        fields = ["name"]
        model = Snake


class BigSnakeForm(SnakeForm):
    class Meta:
        fields = ["name"]
        model = BigSnake

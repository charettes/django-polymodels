from .base import TestCase
from .forms import AnimalForm, BigSnakeForm, SnakeForm
from .models import Animal, BigSnake, Monkey, Snake


class PolymorphicModelFormTests(TestCase):
    def test_invalid_provided_instance(self):
        monkey = Monkey()
        with self.assertRaises(TypeError):
            AnimalForm(instance=monkey)

    def test_instance_based_form_creation(self):
        self.assertIsInstance(AnimalForm(instance=Animal()), AnimalForm)
        self.assertIsInstance(AnimalForm(instance=Snake()), SnakeForm)
        self.assertIsInstance(AnimalForm(instance=BigSnake()), BigSnakeForm)
        self.assertIsInstance(SnakeForm(instance=Snake()), SnakeForm)
        self.assertIsInstance(SnakeForm(instance=BigSnake()), BigSnakeForm)
        self.assertIsInstance(BigSnakeForm(instance=BigSnake()), BigSnakeForm)

    def test_default_instance_type(self):
        form = AnimalForm()
        self.assertIsInstance(form.instance, Animal)
        form = SnakeForm()
        self.assertIsInstance(form.instance, Snake)
        form = BigSnakeForm()
        self.assertIsInstance(form.instance, BigSnake)

    def test_retreival_from_class(self):
        self.assertEqual(AnimalForm[Snake], SnakeForm)

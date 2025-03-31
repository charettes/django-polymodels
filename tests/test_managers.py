from django.core.exceptions import ImproperlyConfigured
from django.db import models

from polymodels.managers import PolymorphicManager

from .base import TestCase
from .models import Animal, BigSnake, HugeSnake, Mammal, Monkey, Snake, Zoo


class PolymorphicQuerySetTest(TestCase):
    def test_select_subclasses(self):
        Animal.objects.create(name="animal")
        Mammal.objects.create(name="mammal")
        Monkey.objects.create(name="monkey")
        Snake.objects.create(name="snake", length=10)
        BigSnake.objects.create(name="big snake", length=101)
        HugeSnake.objects.create(name="huge snake", length=155)
        # Assert `select_subclasses` correctly calls `select_related` and `filter`.
        animals = Animal.objects.select_subclasses()
        animals_expected_query_select_related = {
            "mammal": {"monkey": {}},
            "snake": {},
        }
        self.assertEqual(
            animals.query.select_related, animals_expected_query_select_related
        )
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                animals.all(),
                [
                    "<Animal: animal>",
                    "<Mammal: mammal>",
                    "<Monkey: monkey>",
                    "<Snake: snake>",
                    "<BigSnake: big snake>",
                    "<HugeSnake: huge snake>",
                ],
            )
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                list(animals.iterator()),
                [
                    "<Animal: animal>",
                    "<Mammal: mammal>",
                    "<Monkey: monkey>",
                    "<Snake: snake>",
                    "<BigSnake: big snake>",
                    "<HugeSnake: huge snake>",
                ],
            )
        # Filter out non-mammal (direct subclass)
        animal_mammals = Animal.objects.select_subclasses(Mammal)
        animal_mammals_expected_query_select_related = {"mammal": {"monkey": {}}}
        self.assertEqual(
            animal_mammals.query.select_related,
            animal_mammals_expected_query_select_related,
        )
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                animal_mammals.all(), ["<Mammal: mammal>", "<Monkey: monkey>"]
            )
        # Filter out non-snake (subclass through an abstract one)
        animal_snakes = Animal.objects.select_subclasses(Snake)
        self.assertEqual(animal_snakes.query.select_related, {"snake": {}})
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                animal_snakes.all(),
                ["<Snake: snake>", "<BigSnake: big snake>", "<HugeSnake: huge snake>"],
            )
        # Subclass with only proxies
        snakes = Snake.objects.select_subclasses()
        self.assertFalse(snakes.query.select_related)
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                snakes.all(),
                ["<Snake: snake>", "<BigSnake: big snake>", "<HugeSnake: huge snake>"],
            )
        # Subclass filter proxies
        snake_bigsnakes = Snake.objects.select_subclasses(BigSnake)
        self.assertFalse(snakes.query.select_related)
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                snake_bigsnakes.all(),
                ["<BigSnake: big snake>", "<HugeSnake: huge snake>"],
            )

    def test_select_subclasses_get(self):
        snake = Snake.objects.create(name="snake", length=10)
        self.assertEqual(Animal.objects.select_subclasses().get(), snake)

    def test_select_subclasses_values(self):
        Animal.objects.create(name="animal")
        self.assertQuerysetEqual(
            Animal.objects.select_subclasses().values_list("name", flat=True),
            ["animal"],
            lambda x: x,
        )

    def test_exclude_subclasses(self):
        Animal.objects.create(name="animal")
        Mammal.objects.create(name="first mammal")
        Mammal.objects.create(name="second mammal")
        Monkey.objects.create(name="donkey kong")
        self.assertQuerysetEqual(
            Animal.objects.exclude_subclasses(), ["<Animal: animal>"]
        )
        self.assertQuerysetEqual(
            Mammal.objects.exclude_subclasses(),
            ["<Mammal: first mammal>", "<Mammal: second mammal>"],
        )
        self.assertQuerysetEqual(
            Monkey.objects.exclude_subclasses(), ["<Monkey: donkey kong>"]
        )

    def test_select_subclasses_prefetch_related(self):
        zoo = Zoo.objects.create()
        animal = Animal.objects.create(name="animal")
        mammal = Mammal.objects.create(name="mammal")
        monkey = Monkey.objects.create(name="monkey")
        zoo.animals.add(animal, mammal, monkey)
        other_monkey = Monkey.objects.create(name="monkey")
        monkey.friends.add(other_monkey)
        queryset = Animal.objects.select_subclasses().prefetch_related("zoos")
        with self.assertNumQueries(2):
            self.assertSequenceEqual(
                queryset,
                [
                    animal,
                    mammal,
                    monkey,
                    other_monkey,
                ],
            )
            self.assertSequenceEqual(queryset[0].zoos.all(), [zoo])
            self.assertSequenceEqual(queryset[1].zoos.all(), [zoo])
            self.assertSequenceEqual(queryset[2].zoos.all(), [zoo])
        # Test prefetch related combination.
        queryset = Animal.objects.select_subclasses().prefetch_related(
            "zoos",
            "mammal__monkey__friends",
        )
        with self.assertNumQueries(3):
            self.assertSequenceEqual(
                queryset,
                [
                    animal,
                    mammal,
                    monkey,
                    other_monkey,
                ],
            )
            self.assertSequenceEqual(queryset[0].zoos.all(), [zoo])
            self.assertSequenceEqual(queryset[1].zoos.all(), [zoo])
            self.assertSequenceEqual(queryset[2].zoos.all(), [zoo])
            self.assertSequenceEqual(queryset[2].friends.all(), [other_monkey])
            self.assertSequenceEqual(queryset[3].friends.all(), [monkey])


class PolymorphicManagerTest(TestCase):
    def test_improperly_configured(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "`PolymorphicManager` can only be used on `BasePolymorphicModel` subclasses.",
        ):

            class NonPolymorphicModel(models.Model):
                objects = PolymorphicManager()

                class Meta:
                    app_label = "polymodels"

    def test_proxy_filtering(self):
        """
        Make sure managers attached to proxy models returns a queryset of
        proxies only.
        """
        Snake.objects.create(name="snake", length=1)
        BigSnake.objects.create(name="big snake", length=10)
        HugeSnake.objects.create(name="huge snake", length=100)
        self.assertQuerysetEqual(
            Snake.objects.all(),
            ["<Snake: snake>", "<Snake: big snake>", "<Snake: huge snake>"],
        )
        self.assertQuerysetEqual(
            BigSnake.objects.all(), ["<BigSnake: big snake>", "<BigSnake: huge snake>"]
        )
        self.assertQuerysetEqual(HugeSnake.objects.all(), ["<HugeSnake: huge snake>"])

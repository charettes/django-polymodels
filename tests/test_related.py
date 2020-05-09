from .base import TestCase
from .models import Mammal, Monkey, Zoo


class RelatedManagerTest(TestCase):
    def test_select_subclasses(self):
        """
        Make sure instances are correctly filtered and type casted when calling
        `select_subclasses` on a related manager.
        """
        zoo = Zoo.objects.create()
        yeti = Mammal.objects.create(name='Yeti')
        pepe = Monkey.objects.create(name='Pepe')
        zoo.animals.add(yeti)
        zoo_animals = zoo.animals.select_subclasses()
        self.assertIn(yeti, zoo_animals)
        self.assertNotIn(pepe, zoo_animals)

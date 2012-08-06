#################
django-polymodels
#################

A django application that provides a simple way to retrieve models type casted
to their original ``ContentType``.

************
Installation
************

>>> pip install polymodels

Make sure ``'django.contrib.contenttypes'`` and ``'polymodels'`` are in your `INSTALLED_APPS`::

    INSTALLED_APPS += ('django.contrib.contenttypes', 'polymodels')

*****
Usage
*****
You subclass ``PolymorphicModel`` which is an abstract model class.

::
    
    from django.db import models
    from polymodels.models import PolymorphicModel

    class Animal(PolymorphicModel):
        name = models.CharField(max_length=255)

        def __unicode__(self):
            return self.name

    class Mammal(Animal):
        pass

    class Dog(Mammal):
        pass

    class Reptile(Animal):
        pass

    class Snake(Reptile):
        class Meta:
            proxy = True

Objects are created the same way as usual and their associated ``ContentType`` is saved automatically.

>>> animal = Animal.objects.create(name='animal')
>>> mammal = Mammal.objects.create(name='mammal')
>>> reptile = Reptile.objects.create(name='reptile')
>>> snake = Snake.objects.create(name='snake')

To retreive *type casted* instances from the ``Animal.objects`` manager you just have to use the ``select_subclasses`` method:

>>> Animal.objects.select_subclasses()
[<Animal: animal>, <Mammal: mammal>, <Reptile: reptile>, <Snake: snake>]

You can also retreive a subset of the subclasses by passing them as arguments to ``select_subclass``:

>>> Animal.objects.select_subclasses(Reptile)
[<Reptile: reptile>, <Snake: snake>]

Or directly from subclasses managers:

>>> Reptile.objects.select_subclasses(Snake)
[<Snake: snake>]

Note that you can also retreive original results by avoiding the ``select_subclasses`` call.

>>> Animal.objects.all()
[<Animal: animal>, <Animal: mammal>, <Animal: reptile>, <Animal: snake>]

Each instance of ``PolymorphicModel`` has a ``type_cast`` method that knows how to convert itself to the correct ``ContentType``.

>>> animal_snake = Animal.objects.get(pk=snake.pk)
<Animal: snake>
>>> animal_snake.type_cast()
<Snake: snake>
>>> animal_snake.type_cast(Reptile)
<Reptile: snake>

If the ``PolymorphicModel.content_type`` fields conflicts with one of your existing fields you just have to subclass ``polymodels.models.BasePolymorphicModel`` instead. Just don't forget to indicates which field it should use instead by defining a ``content_type_field_name`` attribute on you model. This field should be a ``ForeignKey`` to ``ContentType``::

    from django.contrib.contenttypes.models import ContentType
    from django.db import models
    from polymodels.models import BasePolymorphicModel

    class MyModel(BasePolymorphicModel):
        content_type_field_name = 'polymorphic_ct'
        polymorphic_ct = models.ForeignKey(ContentType)

************
How it works
************

Under the hood ``select_subclasses`` calls ``seleted_related`` to avoid unnecessary queries and ``filter`` if you pass some classes to it. On querset iteration, the fetched instanced are converted to their correct type by calling ``BasePolymorphicModel.type_cast``. Note that those lookups are cached on class creation to avoid computing them on every single query.

*******
Caution
*******

Until `#16572`_ it's not possible to issue a ``select_related`` over multiple one-to-one relationships. For example, given the models defined `above`_, ``Animal.objects.select_related('mammal__dog')`` would throw a strange ``TypeError``. To avoid this issue, ``select_subclasses`` limits such lookups to one level deep.

.. _#16572: https://code.djangoproject.com/ticket/16572
.. _above: #usage

******************
Note of the author
******************

I'm aware there's already some projects tackling this issue, including `django-polymorphic`_. However I wanted to try implementing this feature in a lightweight way: no ``__metaclass__`` or ``__init__`` overrides. Plus this was really just an extraction of `django-mutant`_'s own mecanism of handling this since I needed it in another project.

.. _django-polymorphic: https://github.com/chrisglass/django_polymorphic
.. _django-mutant: https://github.com/charettes/django-mutant

*******
Credits
*******

* Inspired by a `post of Jeff Elmores`_.

.. _post of Jeff Elmores: http://jeffelmore.org/2010/11/11/automatic-downcasting-of-inherited-models-in-django/

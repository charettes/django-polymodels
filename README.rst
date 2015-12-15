#################
django-polymodels
#################

A django application that provides a simple way to retrieve models type casted
to their original ``ContentType``.

.. image:: https://travis-ci.org/charettes/django-polymodels.svg?branch=master
    :target: https://travis-ci.org/charettes/django-polymodels

.. image:: https://coveralls.io/repos/charettes/django-polymodels/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/charettes/django-polymodels?branch=master

************
Installation
************

>>> pip install django-polymodels

Make sure ``'django.contrib.contenttypes'`` and ``'polymodels'`` are in
your `INSTALLED_APPS`

::

    INSTALLED_APPS += ('django.contrib.contenttypes', 'polymodels')

*****
Usage
*****

Subclass ``PolymorphicModel``, an abstract model class.

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

Objects are created the same way as usual and their associated ``ContentType``
is saved automatically:

>>> animal = Animal.objects.create(name='animal')
>>> mammal = Mammal.objects.create(name='mammal')
>>> reptile = Reptile.objects.create(name='reptile')
>>> snake = Snake.objects.create(name='snake')

To retreive *type casted* instances from the ``Animal.objects`` manager you just
have to use the ``select_subclasses`` method.

>>> Animal.objects.select_subclasses()
[<Animal: animal>, <Mammal: mammal>, <Reptile: reptile>, <Snake: snake>]

You can also retreive a subset of the subclasses by passing them as arguments to
``select_subclass``.

>>> Animal.objects.select_subclasses(Reptile)
[<Reptile: reptile>, <Snake: snake>]

Or directly from subclasses managers.

>>> Reptile.objects.select_subclasses(Snake)
[<Snake: snake>]

Note that you can also retrieve original results by avoiding the
``select_subclasses`` call.

>>> Animal.objects.all()
[<Animal: animal>, <Animal: mammal>, <Animal: reptile>, <Animal: snake>]

It's also possible to select only instances of the model to which the
manager is attached by using the ``exclude_subclasses`` method.

>>> Mammal.objects.all()
[<Mammal: mammal>]

Each instance of ``PolymorphicModel`` has a ``type_cast`` method that knows how
to convert itself to the correct ``ContentType``.

>>> animal_snake = Animal.objects.get(pk=snake.pk)
<Animal: snake>
>>> animal_snake.type_cast()
<Snake: snake>
>>> animal_snake.type_cast(Reptile)
<Reptile: snake>

If the ``PolymorphicModel.content_type`` fields conflicts with one of your
existing fields you just have to subclass
``polymodels.models.BasePolymorphicModel`` and specify which field *polymodels*
should use instead by defining a ``CONTENT_TYPE_FIELD`` attribute on your model.
This field must be a ``ForeignKey`` to ``ContentType``.

::

    from django.contrib.contenttypes.models import ContentType
    from django.db import models
    from polymodels.models import BasePolymorphicModel

    class MyModel(BasePolymorphicModel):
        CONTENT_TYPE_FIELD = 'polymorphic_ct'
        polymorphic_ct = models.ForeignKey(ContentType)

************
How it works
************

Under the hood ``select_subclasses`` calls ``seleted_related`` to avoid
unnecessary queries and ``filter`` if you pass some classes to it. On queryset
iteration, the fetched instanced are converted to their correct type by calling
``BasePolymorphicModel.type_cast``. Note that those lookups are cached on class
creation to avoid computing them on every single query.


******************
Note of the author
******************

I'm aware there's already plenty of existing projects tackling the whole
**model-inheritance-type-casting-thing** such as `django-polymorphic`_. However
I wanted to implement this feature in a lightweight way: no
``__metaclass__`` or ``__init__`` overrides while using django's public API as
much as possible. In the end, this was really just an extraction of
`django-mutant`_'s own mecanism of handling this since I needed it as a
standalone app for another project.

.. _django-polymorphic: https://github.com/chrisglass/django_polymorphic
.. _django-mutant: https://github.com/charettes/django-mutant


**********
Contribute
**********

If you happen to encounter a bug or would like to suggest a feature addition
please `file an issue`_ or `create a pull request`_ containing **tests**.

.. _file an issue: https://github.com/charettes/django-polymodels/issues
.. _create a pull request: https://github.com/charettes/django-polymodels/pulls

*******
Credits
*******

* Inspired by a `post of Jeff Elmores`_.

.. _post of Jeff Elmores: http://jeffelmore.org/2010/11/11/automatic-downcasting-of-inherited-models-in-django/

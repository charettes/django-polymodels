import django.db.models.deletion
from django.db import migrations, models

import polymodels.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [("contenttypes", "0002_remove_content_type_name")]

    operations = [
        migrations.CreateModel(
            name="Animal",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="Trait",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.ContentType",
                    ),
                ),
                (
                    "mammal_type",
                    polymodels.fields.PolymorphicTypeField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        polymorphic_type="tests.Mammal",
                    ),
                ),
                (
                    "snake_type",
                    polymodels.fields.PolymorphicTypeField(
                        on_delete=django.db.models.deletion.CASCADE,
                        polymorphic_type="tests.Snake",
                    ),
                ),
                (
                    "trait_type",
                    polymodels.fields.PolymorphicTypeField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        polymorphic_type="tests.Trait",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Zoo",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "zoos",
                    models.ManyToManyField("Animal", related_name="zoos"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Mammal",
            fields=[
                (
                    "animal_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Animal",
                    ),
                )
            ],
            options={"abstract": False},
            bases=("tests.animal",),
        ),
        migrations.CreateModel(
            name="Snake",
            fields=[
                (
                    "animal_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Animal",
                    ),
                ),
                ("length", models.SmallIntegerField()),
                ("color", models.CharField(blank=True, max_length=100)),
            ],
            options={"ordering": ["id"]},
            bases=("tests.animal",),
        ),
        migrations.AddField(
            model_name="zoo",
            name="animals",
            field=models.ManyToManyField(to="tests.Animal"),
        ),
        migrations.AddField(
            model_name="animal",
            name="content_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="contenttypes.ContentType",
            ),
        ),
        migrations.CreateModel(
            name="AcknowledgedTrait",
            fields=[],
            options={"proxy": True, "indexes": []},
            bases=("tests.trait",),
        ),
        migrations.CreateModel(
            name="Monkey",
            fields=[
                (
                    "mammal_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="tests.Mammal",
                    ),
                ),
                (
                    "friends",
                    models.ManyToManyField(
                        related_name="_monkey_friends_+", to="tests.Monkey"
                    ),
                ),
            ],
            options={"abstract": False},
            bases=("tests.mammal",),
        ),
        migrations.CreateModel(
            name="BigSnake",
            fields=[],
            options={"proxy": True, "indexes": []},
            bases=("tests.snake",),
        ),
        migrations.CreateModel(
            name="HugeSnake",
            fields=[],
            options={"proxy": True, "indexes": []},
            bases=("tests.bigsnake",),
        ),
    ]

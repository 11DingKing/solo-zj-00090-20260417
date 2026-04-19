import base64
from io import BytesIO

import factory
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image
from recipes.models import (
    AmountIngredient,
    Carts,
    Favorites,
    Ingredient,
    Recipe,
    Tag,
)
from users.models import Subscriptions

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}")
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"tag{n}")
    color = factory.Sequence(lambda n: f"#{n:06x}")
    slug = factory.Sequence(lambda n: f"tag{n}")


class IngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ingredient

    name = factory.Sequence(lambda n: f"ingredient{n}")
    measurement_unit = factory.Sequence(lambda n: f"unit{n}")


def create_test_image():
    image = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return ContentFile(buffer.read(), name="test_image.jpg")


class RecipeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Recipe

    name = factory.Sequence(lambda n: f"Recipe {n}")
    author = factory.SubFactory(UserFactory)
    text = factory.Sequence(lambda n: f"This is recipe {n} description.")
    cooking_time = factory.Faker("random_int", min=1, max=120)
    image = factory.LazyFunction(create_test_image)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)

    @factory.post_generation
    def ingredients(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for ingredient_data in extracted:
                if isinstance(ingredient_data, dict):
                    ingredient = ingredient_data.get("ingredient")
                    amount = ingredient_data.get("amount", 1)
                else:
                    ingredient = ingredient_data
                    amount = 1
                AmountIngredientFactory(recipe=self, ingredients=ingredient, amount=amount)


class AmountIngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AmountIngredient

    recipe = factory.SubFactory(RecipeFactory)
    ingredients = factory.SubFactory(IngredientFactory)
    amount = factory.Faker("random_int", min=1, max=100)


class FavoritesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Favorites

    recipe = factory.SubFactory(RecipeFactory)
    user = factory.SubFactory(UserFactory)


class CartsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Carts

    recipe = factory.SubFactory(RecipeFactory)
    user = factory.SubFactory(UserFactory)


class SubscriptionsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscriptions

    author = factory.SubFactory(UserFactory)
    user = factory.SubFactory(UserFactory)

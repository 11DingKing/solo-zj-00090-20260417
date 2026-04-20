import base64
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from tests.factories import (
    CartsFactory,
    FavoritesFactory,
    IngredientFactory,
    RecipeFactory,
    SubscriptionsFactory,
    TagFactory,
    UserFactory,
)

User = get_user_model()

pytest_plugins = ["tests.factories"]


def create_base64_image():
    image = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def admin_user():
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def admin_session_client(admin_user):
    client = APIClient()
    client.login(username=admin_user.username, password="TestPass123!")
    return client


@pytest.fixture
def tag():
    return TagFactory()


@pytest.fixture
def ingredient():
    return IngredientFactory()


@pytest.fixture
def recipe(user):
    tag = TagFactory()
    ingredient = IngredientFactory()
    return RecipeFactory(
        author=user,
        tags=[tag],
        ingredients=[{"ingredient": ingredient, "amount": 10}],
    )


@pytest.fixture
def base64_image():
    return create_base64_image()


@pytest.fixture
def favorite(user, recipe):
    return FavoritesFactory(user=user, recipe=recipe)


@pytest.fixture
def cart(user, recipe):
    return CartsFactory(user=user, recipe=recipe)


@pytest.fixture
def subscription(user):
    author = UserFactory()
    return SubscriptionsFactory(user=user, author=author)


@pytest.fixture
def multiple_recipes_with_same_ingredient(user):
    ingredient = IngredientFactory(name="面粉", measurement_unit="г")
    tag = TagFactory()
    
    recipe1 = RecipeFactory(
        author=user,
        name="Пирог 1",
        tags=[tag],
        ingredients=[{"ingredient": ingredient, "amount": 200}],
    )
    
    recipe2 = RecipeFactory(
        author=user,
        name="Пирог 2",
        tags=[tag],
        ingredients=[{"ingredient": ingredient, "amount": 300}],
    )
    
    return recipe1, recipe2, ingredient

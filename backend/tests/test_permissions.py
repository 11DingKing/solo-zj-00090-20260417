import pytest
from django.contrib.auth import get_user_model
from recipes.models import Carts, Favorites, Recipe
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from tests.factories import IngredientFactory, RecipeFactory, TagFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestAnonymousUserPermissions:
    def test_anonymous_cannot_create_recipe(self, api_client, base64_image):
        tag = TagFactory()
        ingredient = IngredientFactory()

        recipe_data = {
            "name": "Test Recipe",
            "text": "Description",
            "cooking_time": 30,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [tag.id],
            "ingredients": [{"id": ingredient.id, "amount": 100}],
        }

        response = api_client.post("/api/recipes/", recipe_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Recipe.objects.count() == 0

    def test_anonymous_cannot_update_recipe(self, api_client, recipe, base64_image):
        update_data = {
            "name": "Updated Recipe",
            "image": f"data:image/jpeg;base64,{base64_image}",
        }

        response = api_client.patch(
            f"/api/recipes/{recipe.id}/", update_data, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_delete_recipe(self, api_client, recipe):
        response = api_client.delete(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Recipe.objects.filter(id=recipe.id).exists()

    def test_anonymous_cannot_add_to_favorites(self, api_client, recipe):
        response = api_client.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Favorites.objects.count() == 0

    def test_anonymous_cannot_remove_from_favorites(self, api_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)

        response = api_client.delete(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Favorites.objects.filter(user=user, recipe=recipe).exists()

    def test_anonymous_cannot_add_to_shopping_cart(self, api_client, recipe):
        response = api_client.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Carts.objects.count() == 0

    def test_anonymous_cannot_remove_from_shopping_cart(self, api_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)

        response = api_client.delete(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Carts.objects.filter(user=user, recipe=recipe).exists()

    def test_anonymous_cannot_download_shopping_cart(self, api_client):
        response = api_client.get("/api/recipes/download_shopping_cart/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_subscribe(self, api_client):
        author = UserFactory()

        response = api_client.post(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        from users.models import Subscriptions
        assert Subscriptions.objects.count() == 0

    def test_anonymous_cannot_unsubscribe(self, api_client, user):
        from users.models import Subscriptions

        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = api_client.delete(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Subscriptions.objects.filter(user=user, author=author).exists()

    def test_anonymous_cannot_view_subscriptions(self, api_client):
        response = api_client.get("/api/users/subscriptions/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_view_current_user(self, api_client):
        response = api_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_can_view_recipes_list(self, api_client, recipe):
        response = api_client.get("/api/recipes/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_anonymous_can_view_recipe_detail(self, api_client, recipe):
        response = api_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == recipe.id

    def test_anonymous_can_view_tags(self, api_client, tag):
        response = api_client.get("/api/tags/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_anonymous_can_view_ingredients(self, api_client, ingredient):
        response = api_client.get("/api/ingredients/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_anonymous_can_view_users_list(self, api_client, user):
        response = api_client.get("/api/users/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_anonymous_can_view_user_detail(self, api_client, user):
        response = api_client.get(f"/api/users/{user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.id


@pytest.mark.django_db
class TestAuthenticatedUserPermissions:
    def test_authenticated_can_create_recipe(self, authenticated_client, user, base64_image):
        tag = TagFactory()
        ingredient = IngredientFactory()

        recipe_data = {
            "name": "Test Recipe",
            "text": "Description",
            "cooking_time": 30,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [tag.id],
            "ingredients": [{"id": ingredient.id, "amount": 100}],
        }

        response = authenticated_client.post("/api/recipes/", recipe_data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Recipe.objects.count() == 1

    def test_authenticated_can_update_own_recipe(self, authenticated_client, user, recipe, base64_image):
        update_data = {
            "name": "Updated Recipe",
            "image": f"data:image/jpeg;base64,{base64_image}",
        }

        response = authenticated_client.patch(
            f"/api/recipes/{recipe.id}/", update_data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK

    def test_authenticated_cannot_update_others_recipe(self, user, recipe, base64_image):
        other_user = UserFactory()
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=other_user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        update_data = {
            "name": "Malicious Update",
            "image": f"data:image/jpeg;base64,{base64_image}",
        }

        response = client.patch(
            f"/api/recipes/{recipe.id}/", update_data, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authenticated_can_delete_own_recipe(self, authenticated_client, recipe):
        recipe_id = recipe.id

        response = authenticated_client.delete(f"/api/recipes/{recipe_id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Recipe.objects.filter(id=recipe_id).exists()

    def test_authenticated_cannot_delete_others_recipe(self, user, recipe):
        other_user = UserFactory()
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=other_user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.delete(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Recipe.objects.filter(id=recipe.id).exists()

    def test_authenticated_can_add_to_favorites(self, authenticated_client, user, recipe):
        response = authenticated_client.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Favorites.objects.filter(user=user, recipe=recipe).exists()

    def test_authenticated_can_remove_from_favorites(self, authenticated_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)

        response = authenticated_client.delete(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Favorites.objects.filter(user=user, recipe=recipe).exists()

    def test_authenticated_can_add_to_shopping_cart(self, authenticated_client, user, recipe):
        response = authenticated_client.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Carts.objects.filter(user=user, recipe=recipe).exists()

    def test_authenticated_can_remove_from_shopping_cart(self, authenticated_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)

        response = authenticated_client.delete(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Carts.objects.filter(user=user, recipe=recipe).exists()

    def test_authenticated_can_subscribe(self, authenticated_client, user):
        from users.models import Subscriptions

        author = UserFactory()

        response = authenticated_client.post(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Subscriptions.objects.filter(user=user, author=author).exists()

    def test_authenticated_can_unsubscribe(self, authenticated_client, user):
        from users.models import Subscriptions

        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = authenticated_client.delete(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Subscriptions.objects.filter(user=user, author=author).exists()

    def test_authenticated_can_view_subscriptions(self, authenticated_client, user):
        from users.models import Subscriptions

        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = authenticated_client.get("/api/users/subscriptions/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_authenticated_can_view_current_user(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.id


@pytest.mark.django_db
class TestAdminPermissions:
    def test_admin_can_access_admin_interface(self, admin_client):
        response = admin_client.get("/admin/")

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_access_admin_interface(self, authenticated_client):
        response = authenticated_client.get("/admin/")

        assert response.status_code == status.HTTP_302_FOUND or response.status_code == status.HTTP_403_FORBIDDEN

    def test_anonymous_cannot_access_admin_interface(self, api_client):
        response = api_client.get("/admin/")

        assert response.status_code == status.HTTP_302_FOUND

    def test_admin_can_update_any_recipe(self, admin_client, recipe, base64_image):
        update_data = {
            "name": "Admin Updated Recipe",
            "image": f"data:image/jpeg;base64,{base64_image}",
        }

        response = admin_client.patch(
            f"/api/recipes/{recipe.id}/", update_data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_delete_any_recipe(self, admin_client, recipe):
        recipe_id = recipe.id

        response = admin_client.delete(f"/api/recipes/{recipe_id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Recipe.objects.filter(id=recipe_id).exists()

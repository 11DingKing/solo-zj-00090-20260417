import pytest
from recipes.models import Favorites, Recipe
from rest_framework import status
from tests.factories import RecipeFactory, UserFactory


@pytest.mark.django_db
class TestFavoriteCreation:
    def test_add_recipe_to_favorites(self, authenticated_client, user, recipe):
        assert not Favorites.objects.filter(user=user, recipe=recipe).exists()

        response = authenticated_client.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Favorites.objects.filter(user=user, recipe=recipe).exists()

        favorite = Favorites.objects.get(user=user, recipe=recipe)
        assert favorite.user == user
        assert favorite.recipe == recipe

        assert response.data["id"] == recipe.id
        assert response.data["name"] == recipe.name

    def test_add_recipe_to_favorites_without_authentication(self, api_client, recipe):
        response = api_client.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Favorites.objects.count() == 0

    def test_add_nonexistent_recipe_to_favorites(self, authenticated_client):
        response = authenticated_client.post("/api/recipes/999999/favorite/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Favorites.objects.count() == 0

    def test_add_already_favorited_recipe(self, authenticated_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)

        response = authenticated_client.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Favorites.objects.filter(user=user, recipe=recipe).count() == 1


@pytest.mark.django_db
class TestFavoriteDeletion:
    def test_remove_recipe_from_favorites(self, authenticated_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)
        assert Favorites.objects.filter(user=user, recipe=recipe).exists()

        response = authenticated_client.delete(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Favorites.objects.filter(user=user, recipe=recipe).exists()

    def test_remove_recipe_from_favorites_without_authentication(self, api_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)

        response = api_client.delete(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Favorites.objects.filter(user=user, recipe=recipe).exists()

    def test_remove_nonexistent_favorite(self, authenticated_client, recipe):
        response = authenticated_client.delete(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_other_users_favorite(self, recipe):
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token

        other_user = UserFactory()
        Favorites.objects.create(user=other_user, recipe=recipe)

        current_user = UserFactory()
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=current_user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.delete(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Favorites.objects.filter(user=other_user, recipe=recipe).exists()


@pytest.mark.django_db
class TestFavoriteRetrieval:
    def test_get_favorites_list(self, authenticated_client, user):
        recipe1 = RecipeFactory()
        recipe2 = RecipeFactory()
        Favorites.objects.create(user=user, recipe=recipe1)
        Favorites.objects.create(user=user, recipe=recipe2)

        response = authenticated_client.get("/api/recipes/?is_favorited=1")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 2

        recipe_ids = [r["id"] for r in response.data["results"]]
        assert recipe1.id in recipe_ids
        assert recipe2.id in recipe_ids

    def test_recipe_detail_shows_is_favorited_true(self, authenticated_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)

        response = authenticated_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_favorited"] is True

    def test_recipe_detail_shows_is_favorited_false(self, authenticated_client, recipe):
        response = authenticated_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_favorited"] is False

    def test_anonymous_user_sees_is_favorited_false(self, api_client, user, recipe):
        Favorites.objects.create(user=user, recipe=recipe)

        response = api_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_favorited"] is False


@pytest.mark.django_db
class TestFavoriteEdgeCases:
    def test_multiple_users_favorite_same_recipe(self, recipe):
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token

        user1 = UserFactory()
        user2 = UserFactory()

        client1 = APIClient()
        token1, _ = Token.objects.get_or_create(user=user1)
        client1.credentials(HTTP_AUTHORIZATION=f"Token {token1.key}")

        client2 = APIClient()
        token2, _ = Token.objects.get_or_create(user=user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Token {token2.key}")

        response1 = client1.post(f"/api/recipes/{recipe.id}/favorite/")
        response2 = client2.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED
        assert Favorites.objects.count() == 2
        assert Favorites.objects.filter(user=user1, recipe=recipe).exists()
        assert Favorites.objects.filter(user=user2, recipe=recipe).exists()

    def test_user_can_favorite_own_recipe(self, authenticated_client, user):
        recipe = RecipeFactory(author=user)

        response = authenticated_client.post(f"/api/recipes/{recipe.id}/favorite/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Favorites.objects.filter(user=user, recipe=recipe).exists()

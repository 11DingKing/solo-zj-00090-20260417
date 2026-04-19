import pytest
from recipes.models import AmountIngredient, Recipe
from rest_framework import status
from tests.factories import IngredientFactory, TagFactory


@pytest.mark.django_db
class TestRecipeCreation:
    def test_create_recipe_with_tags_and_ingredients(self, authenticated_client, user, base64_image):
        tag1 = TagFactory()
        tag2 = TagFactory()
        ingredient1 = IngredientFactory()
        ingredient2 = IngredientFactory()

        recipe_data = {
            "name": "Test Recipe",
            "text": "This is a test recipe description.",
            "cooking_time": 30,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [tag1.id, tag2.id],
            "ingredients": [
                {"id": ingredient1.id, "amount": 100},
                {"id": ingredient2.id, "amount": 50},
            ],
        }

        response = authenticated_client.post("/api/recipes/", recipe_data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Recipe.objects.count() == 1

        recipe = Recipe.objects.get(id=response.data["id"])
        assert recipe.name == recipe_data["name"]
        assert recipe.text == recipe_data["text"]
        assert recipe.cooking_time == recipe_data["cooking_time"]
        assert recipe.author == user

        assert recipe.tags.count() == 2
        assert tag1 in recipe.tags.all()
        assert tag2 in recipe.tags.all()

        assert recipe.ingredients.count() == 2
        amount1 = AmountIngredient.objects.get(recipe=recipe, ingredients=ingredient1)
        amount2 = AmountIngredient.objects.get(recipe=recipe, ingredients=ingredient2)
        assert amount1.amount == 100
        assert amount2.amount == 50

        assert response.data["name"] == recipe_data["name"]
        assert response.data["cooking_time"] == recipe_data["cooking_time"]
        assert len(response.data["tags"]) == 2
        assert len(response.data["ingredients"]) == 2

    def test_create_recipe_without_authentication(self, api_client, base64_image):
        tag = TagFactory()
        ingredient = IngredientFactory()

        recipe_data = {
            "name": "Test Recipe",
            "text": "This is a test recipe description.",
            "cooking_time": 30,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [tag.id],
            "ingredients": [{"id": ingredient.id, "amount": 100}],
        }

        response = api_client.post("/api/recipes/", recipe_data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Recipe.objects.count() == 0

    def test_create_recipe_without_required_fields(self, authenticated_client, base64_image):
        incomplete_data = {
            "name": "Test Recipe",
        }

        response = authenticated_client.post("/api/recipes/", incomplete_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Recipe.objects.count() == 0

    def test_create_recipe_with_invalid_cooking_time(self, authenticated_client, base64_image):
        tag = TagFactory()
        ingredient = IngredientFactory()

        invalid_data = {
            "name": "Test Recipe",
            "text": "Description",
            "cooking_time": 0,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [tag.id],
            "ingredients": [{"id": ingredient.id, "amount": 100}],
        }

        response = authenticated_client.post("/api/recipes/", invalid_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Recipe.objects.count() == 0

    def test_create_recipe_with_nonexistent_tag(self, authenticated_client, base64_image):
        ingredient = IngredientFactory()

        invalid_data = {
            "name": "Test Recipe",
            "text": "Description",
            "cooking_time": 30,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [999999],
            "ingredients": [{"id": ingredient.id, "amount": 100}],
        }

        response = authenticated_client.post("/api/recipes/", invalid_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Recipe.objects.count() == 0

    def test_create_recipe_with_nonexistent_ingredient(self, authenticated_client, base64_image):
        tag = TagFactory()

        invalid_data = {
            "name": "Test Recipe",
            "text": "Description",
            "cooking_time": 30,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [tag.id],
            "ingredients": [{"id": 999999, "amount": 100}],
        }

        response = authenticated_client.post("/api/recipes/", invalid_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Recipe.objects.count() == 0


@pytest.mark.django_db
class TestRecipeRetrieval:
    def test_get_recipe_list(self, api_client, recipe):
        response = api_client.get("/api/recipes/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    def test_get_recipe_detail(self, api_client, recipe):
        response = api_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == recipe.id
        assert response.data["name"] == recipe.name

    def test_get_nonexistent_recipe(self, api_client):
        response = api_client.get("/api/recipes/999999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRecipeUpdate:
    def test_update_recipe_as_author(self, authenticated_client, user, recipe, base64_image):
        new_tag = TagFactory()
        new_ingredient = IngredientFactory()

        update_data = {
            "name": "Updated Recipe Name",
            "text": "Updated description.",
            "cooking_time": 45,
            "image": f"data:image/jpeg;base64,{base64_image}",
            "tags": [new_tag.id],
            "ingredients": [{"id": new_ingredient.id, "amount": 200}],
        }

        response = authenticated_client.patch(
            f"/api/recipes/{recipe.id}/", update_data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        recipe.refresh_from_db()
        assert recipe.name == update_data["name"]
        assert recipe.text == update_data["text"]
        assert recipe.cooking_time == update_data["cooking_time"]

        assert recipe.tags.count() == 1
        assert new_tag in recipe.tags.all()

        assert recipe.ingredients.count() == 1
        amount = AmountIngredient.objects.get(recipe=recipe)
        assert amount.ingredients == new_ingredient
        assert amount.amount == 200

    def test_update_recipe_as_non_author(self, user, recipe, base64_image):
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        from tests.factories import UserFactory

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

    def test_update_recipe_without_authentication(self, api_client, recipe, base64_image):
        update_data = {
            "name": "Unauthorized Update",
            "image": f"data:image/jpeg;base64,{base64_image}",
        }

        response = api_client.patch(
            f"/api/recipes/{recipe.id}/", update_data, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRecipeDeletion:
    def test_delete_recipe_as_author(self, authenticated_client, recipe):
        recipe_id = recipe.id

        response = authenticated_client.delete(f"/api/recipes/{recipe_id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Recipe.objects.filter(id=recipe_id).exists()

    def test_delete_recipe_as_non_author(self, recipe):
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        from tests.factories import UserFactory

        other_user = UserFactory()
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=other_user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.delete(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Recipe.objects.filter(id=recipe.id).exists()

    def test_delete_recipe_without_authentication(self, api_client, recipe):
        response = api_client.delete(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Recipe.objects.filter(id=recipe.id).exists()

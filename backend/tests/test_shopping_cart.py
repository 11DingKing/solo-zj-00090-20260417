import pytest
from recipes.models import AmountIngredient, Carts, Ingredient
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from tests.factories import IngredientFactory, RecipeFactory, TagFactory, UserFactory


@pytest.mark.django_db
class TestShoppingCartCreation:
    def test_add_recipe_to_shopping_cart(self, authenticated_client, user, recipe):
        assert not Carts.objects.filter(user=user, recipe=recipe).exists()

        response = authenticated_client.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Carts.objects.filter(user=user, recipe=recipe).exists()

        cart_item = Carts.objects.get(user=user, recipe=recipe)
        assert cart_item.user == user
        assert cart_item.recipe == recipe

        assert response.data["id"] == recipe.id
        assert response.data["name"] == recipe.name

    def test_add_recipe_to_shopping_cart_without_authentication(self, api_client, recipe):
        response = api_client.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Carts.objects.count() == 0

    def test_add_nonexistent_recipe_to_shopping_cart(self, authenticated_client):
        response = authenticated_client.post("/api/recipes/999999/shopping_cart/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Carts.objects.count() == 0

    def test_add_already_added_recipe(self, authenticated_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)

        response = authenticated_client.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Carts.objects.filter(user=user, recipe=recipe).count() == 1


@pytest.mark.django_db
class TestShoppingCartDeletion:
    def test_remove_recipe_from_shopping_cart(self, authenticated_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)
        assert Carts.objects.filter(user=user, recipe=recipe).exists()

        response = authenticated_client.delete(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Carts.objects.filter(user=user, recipe=recipe).exists()

    def test_remove_recipe_from_shopping_cart_without_authentication(self, api_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)

        response = api_client.delete(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Carts.objects.filter(user=user, recipe=recipe).exists()

    def test_remove_nonexistent_cart_item(self, authenticated_client, recipe):
        response = authenticated_client.delete(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_other_users_cart_item(self, recipe):
        other_user = UserFactory()
        Carts.objects.create(user=other_user, recipe=recipe)

        current_user = UserFactory()
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=current_user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.delete(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Carts.objects.filter(user=other_user, recipe=recipe).exists()


@pytest.mark.django_db
class TestShoppingCartRetrieval:
    def test_get_shopping_cart_list(self, authenticated_client, user):
        recipe1 = RecipeFactory()
        recipe2 = RecipeFactory()
        Carts.objects.create(user=user, recipe=recipe1)
        Carts.objects.create(user=user, recipe=recipe2)

        response = authenticated_client.get("/api/recipes/?is_in_shopping_cart=1")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 2

        recipe_ids = [r["id"] for r in response.data["results"]]
        assert recipe1.id in recipe_ids
        assert recipe2.id in recipe_ids

    def test_recipe_detail_shows_is_in_shopping_cart_true(self, authenticated_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)

        response = authenticated_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_in_shopping_cart"] is True

    def test_recipe_detail_shows_is_in_shopping_cart_false(self, authenticated_client, recipe):
        response = authenticated_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_in_shopping_cart"] is False

    def test_anonymous_user_sees_is_in_shopping_cart_false(self, api_client, user, recipe):
        Carts.objects.create(user=user, recipe=recipe)

        response = api_client.get(f"/api/recipes/{recipe.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_in_shopping_cart"] is False


@pytest.mark.django_db
class TestShoppingCartDownload:
    def test_download_shopping_cart(self, authenticated_client, user):
        tag = TagFactory()
        ingredient = IngredientFactory(name="面粉", measurement_unit="г")
        recipe = RecipeFactory(
            tags=[tag],
            ingredients=[{"ingredient": ingredient, "amount": 200}],
        )
        Carts.objects.create(user=user, recipe=recipe)

        response = authenticated_client.get("/api/recipes/download_shopping_cart/")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "text.txt; charset=utf-8"
        assert "attachment" in response["Content-Disposition"]
        assert "面粉" in response.content.decode("utf-8")
        assert "200" in response.content.decode("utf-8")

    def test_download_shopping_cart_without_authentication(self, api_client):
        response = api_client.get("/api/recipes/download_shopping_cart/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_download_empty_shopping_cart(self, authenticated_client):
        response = authenticated_client.get("/api/recipes/download_shopping_cart/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestShoppingCartIngredientMerging:
    def test_same_ingredient_from_different_recipes_merged(self, user):
        tag = TagFactory()
        ingredient = IngredientFactory(name="面粉", measurement_unit="г")

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

        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        client.post(f"/api/recipes/{recipe1.id}/shopping_cart/")
        client.post(f"/api/recipes/{recipe2.id}/shopping_cart/")

        assert Carts.objects.filter(user=user).count() == 2

        response = client.get("/api/recipes/download_shopping_cart/")

        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")

        assert "面粉" in content
        assert "500" in content

    def test_multiple_ingredients_with_different_units(self, user):
        tag = TagFactory()
        ingredient1 = IngredientFactory(name="面粉", measurement_unit="г")
        ingredient2 = IngredientFactory(name="牛奶", measurement_unit="мл")
        ingredient3 = IngredientFactory(name="яйцо", measurement_unit="шт")

        recipe1 = RecipeFactory(
            author=user,
            name="Пирог",
            tags=[tag],
            ingredients=[
                {"ingredient": ingredient1, "amount": 200},
                {"ingredient": ingredient2, "amount": 100},
            ],
        )

        recipe2 = RecipeFactory(
            author=user,
            name="Омлет",
            tags=[tag],
            ingredients=[
                {"ingredient": ingredient2, "amount": 50},
                {"ingredient": ingredient3, "amount": 3},
            ],
        )

        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        client.post(f"/api/recipes/{recipe1.id}/shopping_cart/")
        client.post(f"/api/recipes/{recipe2.id}/shopping_cart/")

        response = client.get("/api/recipes/download_shopping_cart/")

        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")

        assert "面粉" in content
        assert "200" in content
        assert "牛奶" in content
        assert "150" in content
        assert "яйцо" in content
        assert "3" in content


@pytest.mark.django_db
class TestShoppingCartEdgeCases:
    def test_multiple_users_same_recipe_in_cart(self, recipe):
        user1 = UserFactory()
        user2 = UserFactory()

        client1 = APIClient()
        token1, _ = Token.objects.get_or_create(user=user1)
        client1.credentials(HTTP_AUTHORIZATION=f"Token {token1.key}")

        client2 = APIClient()
        token2, _ = Token.objects.get_or_create(user=user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Token {token2.key}")

        response1 = client1.post(f"/api/recipes/{recipe.id}/shopping_cart/")
        response2 = client2.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED
        assert Carts.objects.count() == 2
        assert Carts.objects.filter(user=user1, recipe=recipe).exists()
        assert Carts.objects.filter(user=user2, recipe=recipe).exists()

    def test_user_can_add_own_recipe_to_cart(self, authenticated_client, user):
        recipe = RecipeFactory(author=user)

        response = authenticated_client.post(f"/api/recipes/{recipe.id}/shopping_cart/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Carts.objects.filter(user=user, recipe=recipe).exists()

    def test_adding_recipe_to_cart_does_not_affect_other_users(self, user, recipe):
        other_user = UserFactory()
        Carts.objects.create(user=other_user, recipe=recipe)

        assert not Carts.objects.filter(user=user, recipe=recipe).exists()

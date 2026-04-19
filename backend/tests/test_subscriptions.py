import pytest
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from tests.factories import RecipeFactory, UserFactory
from users.models import Subscriptions


@pytest.mark.django_db
class TestSubscriptionCreation:
    def test_subscribe_to_author(self, authenticated_client, user):
        author = UserFactory()
        assert not Subscriptions.objects.filter(user=user, author=author).exists()

        response = authenticated_client.post(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_201_CREATED
        assert Subscriptions.objects.filter(user=user, author=author).exists()

        subscription = Subscriptions.objects.get(user=user, author=author)
        assert subscription.user == user
        assert subscription.author == author

        assert response.data["id"] == author.id
        assert response.data["email"] == author.email
        assert response.data["is_subscribed"] is True

    def test_subscribe_without_authentication(self, api_client):
        author = UserFactory()

        response = api_client.post(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Subscriptions.objects.count() == 0

    def test_subscribe_to_nonexistent_author(self, authenticated_client):
        response = authenticated_client.post("/api/users/999999/subscribe/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Subscriptions.objects.count() == 0

    def test_subscribe_to_yourself(self, authenticated_client, user):
        response = authenticated_client.post(f"/api/users/{user.id}/subscribe/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Subscriptions.objects.count() == 0

    def test_subscribe_to_already_subscribed_author(self, authenticated_client, user):
        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = authenticated_client.post(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Subscriptions.objects.filter(user=user, author=author).count() == 1


@pytest.mark.django_db
class TestSubscriptionDeletion:
    def test_unsubscribe_from_author(self, authenticated_client, user):
        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)
        assert Subscriptions.objects.filter(user=user, author=author).exists()

        response = authenticated_client.delete(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Subscriptions.objects.filter(user=user, author=author).exists()

    def test_unsubscribe_without_authentication(self, api_client, user):
        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = api_client.delete(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Subscriptions.objects.filter(user=user, author=author).exists()

    def test_unsubscribe_from_nonexistent_subscription(self, authenticated_client):
        author = UserFactory()

        response = authenticated_client.delete(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unsubscribe_from_other_users_subscription(self):
        from tests.factories import UserFactory

        user1 = UserFactory()
        user2 = UserFactory()
        author = UserFactory()

        Subscriptions.objects.create(user=user1, author=author)

        client2 = APIClient()
        token2, _ = Token.objects.get_or_create(user=user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Token {token2.key}")

        response = client2.delete(f"/api/users/{author.id}/subscribe/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Subscriptions.objects.filter(user=user1, author=author).exists()


@pytest.mark.django_db
class TestSubscriptionRetrieval:
    def test_get_subscriptions_list(self, authenticated_client, user):
        author1 = UserFactory()
        author2 = UserFactory()
        Subscriptions.objects.create(user=user, author=author1)
        Subscriptions.objects.create(user=user, author=author2)

        response = authenticated_client.get("/api/users/subscriptions/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 2

        author_ids = [a["id"] for a in response.data["results"]]
        assert author1.id in author_ids
        assert author2.id in author_ids

    def test_user_profile_shows_is_subscribed_true(self, authenticated_client, user):
        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = authenticated_client.get(f"/api/users/{author.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_subscribed"] is True

    def test_user_profile_shows_is_subscribed_false(self, authenticated_client):
        author = UserFactory()

        response = authenticated_client.get(f"/api/users/{author.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_subscribed"] is False

    def test_own_profile_shows_is_subscribed_false(self, authenticated_client, user):
        response = authenticated_client.get(f"/api/users/{user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_subscribed"] is False

    def test_anonymous_user_sees_is_subscribed_false(self, api_client, user):
        author = UserFactory()
        Subscriptions.objects.create(user=user, author=author)

        response = api_client.get(f"/api/users/{author.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_subscribed"] is False

    def test_subscription_includes_recipes_count(self, authenticated_client, user):
        author = UserFactory()
        RecipeFactory.create_batch(3, author=author)
        Subscriptions.objects.create(user=user, author=author)

        response = authenticated_client.get("/api/users/subscriptions/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["recipes_count"] == 3

    def test_subscription_includes_recipes(self, authenticated_client, user):
        author = UserFactory()
        recipe = RecipeFactory(author=author)
        Subscriptions.objects.create(user=user, author=author)

        response = authenticated_client.get("/api/users/subscriptions/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"][0]["recipes"]) == 1
        assert response.data["results"][0]["recipes"][0]["id"] == recipe.id


@pytest.mark.django_db
class TestSubscriptionEdgeCases:
    def test_multiple_users_subscribe_to_same_author(self):
        author = UserFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        client1 = APIClient()
        token1, _ = Token.objects.get_or_create(user=user1)
        client1.credentials(HTTP_AUTHORIZATION=f"Token {token1.key}")

        client2 = APIClient()
        token2, _ = Token.objects.get_or_create(user=user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Token {token2.key}")

        response1 = client1.post(f"/api/users/{author.id}/subscribe/")
        response2 = client2.post(f"/api/users/{author.id}/subscribe/")

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED
        assert Subscriptions.objects.count() == 2
        assert Subscriptions.objects.filter(user=user1, author=author).exists()
        assert Subscriptions.objects.filter(user=user2, author=author).exists()

    def test_author_can_have_subscribers(self, user):
        author = UserFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        Subscriptions.objects.create(user=user1, author=author)
        Subscriptions.objects.create(user=user2, author=author)

        assert author.subscribers.count() == 2
        assert user1 in [sub.user for sub in author.subscribers.all()]
        assert user2 in [sub.user for sub in author.subscribers.all()]

    def test_user_can_have_multiple_subscriptions(self, user):
        author1 = UserFactory()
        author2 = UserFactory()
        author3 = UserFactory()

        Subscriptions.objects.create(user=user, author=author1)
        Subscriptions.objects.create(user=user, author=author2)
        Subscriptions.objects.create(user=user, author=author3)

        assert user.subscriptions.count() == 3
        assert author1 in [sub.author for sub in user.subscriptions.all()]
        assert author2 in [sub.author for sub in user.subscriptions.all()]
        assert author3 in [sub.author for sub in user.subscriptions.all()]

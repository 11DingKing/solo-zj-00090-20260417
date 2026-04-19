import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    def test_successful_registration(self, api_client):
        registration_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "password": "StrongPass123!",
        }

        response = api_client.post("/api/users/", registration_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email=registration_data["email"]).exists()
        
        user = User.objects.get(email=registration_data["email"])
        assert user.username == registration_data["username"]
        assert user.first_name == registration_data["first_name"]
        assert user.last_name == registration_data["last_name"]
        assert user.check_password(registration_data["password"])
        assert response.data["email"] == registration_data["email"]
        assert response.data["username"] == registration_data["username"]

    def test_duplicate_email_registration(self, api_client, user):
        registration_data = {
            "email": user.email,
            "username": "differentuser",
            "first_name": "Different",
            "last_name": "User",
            "password": "StrongPass123!",
        }

        response = api_client.post("/api/users/", registration_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 1

    def test_duplicate_username_registration(self, api_client, user):
        registration_data = {
            "email": "different@example.com",
            "username": user.username,
            "first_name": "Different",
            "last_name": "User",
            "password": "StrongPass123!",
        }

        response = api_client.post("/api/users/", registration_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 1

    def test_registration_without_required_fields(self, api_client):
        incomplete_data = {
            "email": "test@example.com",
        }

        response = api_client.post("/api/users/", incomplete_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 0

    def test_registration_with_invalid_email(self, api_client):
        invalid_data = {
            "email": "invalid-email",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "StrongPass123!",
        }

        response = api_client.post("/api/users/", invalid_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 0


@pytest.mark.django_db
class TestUserLogin:
    def test_successful_login(self, api_client, user):
        login_data = {
            "email": user.email,
            "password": "TestPass123!",
        }

        response = api_client.post("/api/auth/token/login/", login_data)

        assert response.status_code == status.HTTP_200_OK
        assert "auth_token" in response.data
        
        token = Token.objects.get(user=user)
        assert response.data["auth_token"] == token.key

    def test_login_with_wrong_password(self, api_client, user):
        login_data = {
            "email": user.email,
            "password": "WrongPassword123!",
        }

        response = api_client.post("/api/auth/token/login/", login_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "auth_token" not in response.data

    def test_login_with_nonexistent_email(self, api_client):
        login_data = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!",
        }

        response = api_client.post("/api/auth/token/login/", login_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_without_credentials(self, api_client):
        response = api_client.post("/api/auth/token/login/", {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogout:
    def test_successful_logout(self, authenticated_client, user):
        token = Token.objects.get(user=user)
        
        response = authenticated_client.post("/api/auth/token/logout/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Token.objects.filter(key=token.key).exists()

    def test_logout_without_authentication(self, api_client):
        response = api_client.post("/api/auth/token/logout/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenAuthentication:
    def test_access_protected_endpoint_with_valid_token(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["username"] == user.username

    def test_access_protected_endpoint_without_token(self, api_client):
        response = api_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_endpoint_with_invalid_token(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Token invalid_token_123")
        
        response = api_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_expired_scenario(self, authenticated_client, user):
        token = Token.objects.get(user=user)
        token.delete()
        
        response = authenticated_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    def test_get_current_user_profile(self, authenticated_client, user):
        response = authenticated_client.get("/api/users/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.id
        assert response.data["email"] == user.email
        assert response.data["username"] == user.username
        assert response.data["first_name"] == user.first_name
        assert response.data["last_name"] == user.last_name

    def test_get_user_profile_by_id(self, authenticated_client, user):
        other_user = UserFactory()
        
        response = authenticated_client.get(f"/api/users/{other_user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == other_user.id
        assert response.data["email"] == other_user.email

    def test_list_users_authenticated(self, authenticated_client):
        UserFactory.create_batch(3)
        
        response = authenticated_client.get("/api/users/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 4

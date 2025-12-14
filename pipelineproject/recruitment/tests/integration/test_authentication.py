import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
def test_jwt_authentication_success():
    user = User.objects.create_user(
        username="recruiter",
        password="strong-password"
    )

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    response = client.get("/recruitments/jobs/")
    assert response.status_code == 200

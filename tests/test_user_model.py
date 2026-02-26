import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserModel:
    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="pass123",
            name="John",
        )
        assert user.email == "user@example.com"
        assert user.name == "John"
        assert user.check_password("pass123")
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="pass123")

    def test_email_is_unique(self):
        User.objects.create_user(email="dup@example.com", password="pass123")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="dup@example.com", password="pass456")

    def test_kakao_id_nullable_and_unique(self):
        user1 = User.objects.create_user(
            email="a@example.com", password="pass123"
        )
        assert user1.kakao_id is None

        user2 = User.objects.create_user(
            email="b@example.com", password="pass123", kakao_id="kakao_123"
        )
        assert user2.kakao_id == "kakao_123"

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="c@example.com", password="pass123", kakao_id="kakao_123"
            )

    def test_password_nullable_for_social_login(self):
        user = User.objects.create_user(
            email="social@example.com",
            password=None,
            kakao_id="kakao_456",
        )
        assert user.has_usable_password() is False

    def test_default_point_is_1000000(self):
        user = User.objects.create_user(
            email="point@example.com", password="pass123"
        )
        assert user.point == 1_000_000

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="admin123"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_str_returns_email(self):
        user = User.objects.create_user(
            email="str@example.com", password="pass123"
        )
        assert str(user) == "str@example.com"

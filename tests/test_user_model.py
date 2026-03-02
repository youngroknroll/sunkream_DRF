import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserModel:
    def _create_user(self, **overrides):
        payload = {
            "email": "user@example.com",
            "password": "pass123",
            "name": "John",
        }
        payload.update(overrides)
        return User.objects.create_user(**payload)

    def test_일반유저를_생성할수있다(self):
        user = self._create_user()
        assert user.email == "user@example.com"
        assert user.name == "John"
        assert user.check_password("pass123")
        assert user.is_active is True
        assert user.is_staff is False

    def test_이메일이없으면_유저생성에_실패한다(self):
        with pytest.raises(ValueError):
            self._create_user(email="", password="pass123")

    def test_이메일은_중복될수없다(self):
        self._create_user(email="dup@example.com")
        with pytest.raises(IntegrityError):
            self._create_user(email="dup@example.com", password="pass456")

    def test_카카오아이디는_null을_허용한다(self):
        user1 = self._create_user(email="a@example.com")
        assert user1.kakao_id is None

    def test_카카오아이디는_중복될수없다(self):
        self._create_user(email="b@example.com", kakao_id="kakao_123")

        with pytest.raises(IntegrityError):
            self._create_user(email="c@example.com", kakao_id="kakao_123")

    def test_카카오아이디가_저장된다(self):
        user2 = self._create_user(email="b@example.com", kakao_id="kakao_123")
        assert user2.kakao_id == "kakao_123"

    def test_소셜로그인유저는_비밀번호가_없을수있다(self):
        user = self._create_user(email="social@example.com", password=None, kakao_id="kakao_456")
        assert user.has_usable_password() is False

    def test_기본포인트는_100만원이다(self):
        user = self._create_user(email="point@example.com")
        assert user.point == 1_000_000

    def test_슈퍼유저를_생성할수있다(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="admin123"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_문자열표현은_이메일이다(self):
        user = self._create_user(email="str@example.com")
        assert str(user) == "str@example.com"

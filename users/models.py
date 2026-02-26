from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from core.models import TimeStampModel
from users.managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin, TimeStampModel):
    email = models.EmailField(unique=True)
    kakao_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    name = models.CharField(max_length=50, blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    point = models.PositiveIntegerField(default=1_000_000)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

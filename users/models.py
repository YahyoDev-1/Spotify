from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Maxsus foydalanuvchi modeli.

    Hozircha standart maydonlar (username, email, password, ...) yetarli,
    lekin loyiha boshidayoq custom model qilib qo'yamiz — keyinchalik
    avatar, bio, premium kabi maydonlar qo'shish oson bo'ladi.
    """
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.username

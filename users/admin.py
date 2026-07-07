from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

# Django'ning tayyor UserAdmin'i parolni to'g'ri boshqaradi (hash, o'zgartirish formasi)
admin.site.register(User, UserAdmin)

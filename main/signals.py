"""Kesh invalidatsiyasi uchun signallar.

Signal — Django'ning "hodisa e'loni": model saqlanganda/o'chirilganda
Django xabar tarqatadi, biz unga quloq solamiz. Bu yozuv QAYERDA
sodir bo'lishidan qat'i nazar ishlaydi: API view, admin panel, shell.
View ichida invalidatsiya qilsak — admin orqali o'zgarish keshni
yangilamay qolardi.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .cache import bump_version, SONGS_VERSION_KEY, GENRES_VERSION_KEY
from .models import Song, Like, Album, Genre


@receiver([post_save, post_delete], sender=Song)
def invalidate_songs_on_song_change(sender, **kwargs):
    bump_version(SONGS_VERSION_KEY)


@receiver([post_save, post_delete], sender=Like)
def invalidate_songs_on_like_change(sender, **kwargs):
    # likes_count qo'shiqlar JSON'ida bor — like o'zgarsa ro'yxat eskiradi
    bump_version(SONGS_VERSION_KEY)


@receiver([post_save, post_delete], sender=Album)
def invalidate_songs_on_album_change(sender, **kwargs):
    # album nomi qo'shiqlar JSON'ida bor (SlugRelatedField)
    bump_version(SONGS_VERSION_KEY)


@receiver([post_save, post_delete], sender=Genre)
def invalidate_on_genre_change(sender, **kwargs):
    # janr nomi ham qo'shiqlar JSON'ida, ham /genres/ ro'yxatida
    bump_version(GENRES_VERSION_KEY)
    bump_version(SONGS_VERSION_KEY)

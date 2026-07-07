from django.conf import settings
from django.db import models
from django.core.validators import (
    FileExtensionValidator
)
from django_countries.fields import CountryField


class Genre(models.Model):
    """Janr modeli — varchar takrorlash o'rniga alohida jadval (normalizatsiya)"""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Singer(models.Model):
    """Qo'shiqchi modeli"""
    name = models.CharField(
        max_length=100,
        db_index=True  # Ismga qidiruv uchun
    )
    birthday = models.DateField(blank=True, null=True)
    country = CountryField(blank_label='(Select country)', blank=True, null=True)

    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Meta
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['country']),
        ]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Singer: {self.name}>"


class Album(models.Model):
    """Albom modeli"""
    name = models.CharField(
        max_length=100,
        db_index=True
    )
    image = models.ImageField(
        upload_to='albums/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text='Album muqovasi'
    )
    release_date = models.DateField(
        blank=True,
        null=True,
        help_text='Albom chiqqan sana'
    )
    singer = models.ForeignKey(
        Singer,
        on_delete=models.PROTECT,  # Singer o'chirilmasin agar albom bo'lsa
        related_name='albums',  # Singer.albums.all()
        help_text='Qo\'shiqchi'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Meta
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['singer', '-created_at']),
        ]
        unique_together = [['name', 'singer']]  # Ayni qo'shiqchi 1 ta albomga 1 nomi

    def __str__(self):
        return f"{self.name} ({self.singer.name})"


class Song(models.Model):
    """Qo'shiq modeli"""
    name = models.CharField(
        max_length=100,
        db_index=True
    )
    genre = models.ForeignKey(
        Genre,
        on_delete=models.PROTECT,  # Janrni o'chirsak, qo'shiqlar "yetim" qolmasin
        related_name='songs',  # Genre.songs.all()
        help_text='Janr'
    )
    duration = models.DurationField(
        help_text='Qo\'shiqning davomiyligi'
    )
    file = models.FileField(
        upload_to='songs/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['mp3', 'wav', 'flac', 'aac'],
                message='Ruxsat: MP3, WAV, FLAC, AAC'
            )
        ],
        help_text='Audio fayli'
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='songs',  # Album.songs.all()
        help_text='Albom'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Meta
    class Meta:
        ordering = ['album', 'name']
        indexes = [
            models.Index(fields=['album', 'genre']),
            models.Index(fields=['genre', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.album.name}"

    def get_duration_display(self):
        """Davomiylikni human-readable format-da ko'rsatish"""
        if self.duration:
            total_seconds = int(self.duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:02d}"
        return "Unknown"


class Playlist(models.Model):
    """Foydalanuvchi playlisti"""
    name = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # 'users.User' deb qattiq yozmaymiz
        on_delete=models.CASCADE,  # User o'chsa, playlistlari ham o'chadi
        related_name='playlists',  # user.playlists.all()
    )
    is_public = models.BooleanField(
        default=True,
        help_text='Ochiq playlist boshqalarga ko\'rinadi'
    )
    # M2M bog'lanish, lekin oraliq jadval O'ZIMIZNIKI — chunki order kerak
    songs = models.ManyToManyField(
        Song,
        through='PlaylistSong',
        related_name='playlists',  # song.playlists.all()
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Bitta foydalanuvchida bir xil nomli ikkita playlist bo'lmasin
            models.UniqueConstraint(fields=['user', 'name'], name='unique_playlist_per_user'),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class PlaylistSong(models.Model):
    """Playlist va Song orasidagi junction jadval — qo'shiq tartibi bilan"""
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='playlist_songs',
    )
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(
        default=0,
        help_text='Playlistdagi tartib raqami'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'added_at']
        constraints = [
            # Bitta qo'shiq bitta playlistga faqat bir marta qo'shiladi
            models.UniqueConstraint(fields=['playlist', 'song'], name='unique_song_in_playlist'),
        ]

    def __str__(self):
        return f"{self.playlist.name} #{self.order}: {self.song.name}"


class Like(models.Model):
    """Foydalanuvchi qo'shiqni yoqtirishi"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='likes',  # song.likes.count() — necha kishi yoqtirgan
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Bir odam bir qo'shiqqa faqat bitta like
            models.UniqueConstraint(fields=['user', 'song'], name='unique_like'),
        ]

    def __str__(self):
        return f"{self.user.username} ❤ {self.song.name}"


class Follow(models.Model):
    """Foydalanuvchining qo'shiqchiga obunasi"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',  # user.following.all() — kimlarga obuna
    )
    singer = models.ForeignKey(
        Singer,
        on_delete=models.CASCADE,
        related_name='followers',  # singer.followers.count() — obunachilar soni
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Bir artistga faqat bir marta obuna bo'lish mumkin
            models.UniqueConstraint(fields=['user', 'singer'], name='unique_follow'),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.singer.name}"

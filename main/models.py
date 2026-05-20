from django.db import models
from django_countries.fields import CountryField

# Create your models here.
from django.db import models
from django.core.validators import (
    FileExtensionValidator
)
from django_countries.fields import CountryField

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
    genre = models.CharField(
        max_length=100,
        db_index=True,  # Genre bo'yicha filterlash uchun
        choices=[
            ('pop', 'Pop'),
            ('rock', 'Rock'),
            ('jazz', 'Jazz'),
            ('classical', 'Classical'),
            ('other', 'Other'),
        ]
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

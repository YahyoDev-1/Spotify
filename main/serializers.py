import datetime

from rest_framework import serializers
from django_countries.serializer_fields import CountryField

from .models import Genre, Singer, Album, Song, Playlist, PlaylistSong

from mutagen import File as MusicFile


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'


class SingerSerializer(serializers.ModelSerializer):
    # ModelSerializer Country obyektini JSON'ga o'gira olmaydi —
    # django-countries'ning maxsus DRF maydonini ishlatamiz ("UZ" ko'rinishida)
    country = CountryField(required=False, allow_blank=True, allow_null=True)
    # ViewSet queryset'idagi annotate()'dan keladi — SQL COUNT natijasi
    followers_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Singer
        fields = '__all__'

    def validate_name(self, name):
        if len(name) < 3:
            raise serializers.ValidationError(
                'Singer must be at least 3 characters'
            )
        return name

class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = '__all__'


class SongSerializer(serializers.ModelSerializer):
    album = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Album.objects.all(),
    )
    genre = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Genre.objects.all(),
    )
    # ViewSet queryset'idagi annotate()'dan keladi — SQL COUNT natijasi
    likes_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Song
        fields = ('id', 'name', 'genre', 'file', 'album', 'duration', 'likes_count',)
    #     Duration avtomatik hisoblanadi, foydalanuvchi kiritmaydi
        read_only_fields = ('duration',)

    def validate(self, data):
        file = data.get('file')

        if file:
            try:
                # Fayl ko'rsatkichini boshiga qaytaramiz (xavfsizlik uchun)
                file.seek(0)

                audio = MusicFile(file)

                if audio is not None and audio.info:

                    seconds = audio.info.length

                    if seconds > 7 * 60:
                        raise serializers.ValidationError(
                            {"audio_file": "Qo'shiq davomiyligi 7 minutdan ko'p bo'lmasligi kerak."}
                        )
                    data['duration'] = datetime.timedelta(seconds=int(seconds))
                else:
                    raise serializers.ValidationError(
                        {"audio_file": "Yuklangan fayl yaroqli audio fayl emas yoki formati qo'llab-quvvatlanmaydi."}
                    )

            except Exception as e:
                raise serializers.ValidationError(
                    {"audio_file": f"Audio faylni tahlil qilishda xatolik yuz berdi: {str(e)}"}
                )
        return data


class SongMiniSerializer(serializers.ModelSerializer):
    """Playlist ichida ko'rsatish uchun yengil variant — ortiqcha maydonlarsiz"""
    album = serializers.ReadOnlyField(source='album.name')

    class Meta:
        model = Song
        fields = ('id', 'name', 'album', 'duration')


class PlaylistSongSerializer(serializers.ModelSerializer):
    song = SongMiniSerializer(read_only=True)

    class Meta:
        model = PlaylistSong
        fields = ('song', 'order', 'added_at')


class PlaylistSerializer(serializers.ModelSerializer):
    # Egasi so'rovdan olinadi (perform_create), klient yubora olmaydi
    user = serializers.ReadOnlyField(source='user.username')
    # related_name='playlist_songs' orqali tartiblangan qo'shiqlar
    songs = PlaylistSongSerializer(source='playlist_songs', many=True, read_only=True)
    songs_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ('id', 'name', 'user', 'is_public', 'songs_count', 'songs', 'created_at')

    def get_songs_count(self, obj) -> int:
        # -> int type hint: drf-spectacular sxemada to'g'ri "integer" deb belgilaydi.
        # len() ishlatamiz — prefetch qilingan ro'yxatni sanaydi, yangi SQL yubormaydi
        return len(obj.playlist_songs.all())
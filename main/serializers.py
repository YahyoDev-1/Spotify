import datetime

from rest_framework import serializers

from .models import Singer, Album, Song

from mutagen import File as MusicFile


class SingerSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Song
        fields = ('id', 'name', 'genre', 'file', 'album', 'duration',)
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
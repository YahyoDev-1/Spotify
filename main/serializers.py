from rest_framework import serializers

from .models import Singer, Album, Song


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
    album = serializers.StringRelatedField(
        read_only=True,
    )
    class Meta:
        model = Song
        fields = '__all__'

    def validate_duration(self, duration):
        # 'duration' bu yerda allaqachon timedelta obyekti hisoblanadi.
        # total_seconds() umumiy soniyalarni qaytaradi (masalan, 6:00 -> 360.0 soniya).
        # 7 minutimiz esa: 7 * 60 = 420 soniya bo'ladi.

        if duration and duration.total_seconds() > 7 * 60:
            raise serializers.ValidationError(
                'Qo\'shiq davomiyligi 7 minutdan ko\'p bo\'lmasligi kerak.'
            )

        return duration
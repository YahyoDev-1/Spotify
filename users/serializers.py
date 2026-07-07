from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Ro'yxatdan o'tish uchun serializer"""
    password = serializers.CharField(
        write_only=True,  # Javobda hech qachon qaytarilmaydi
        validators=[validate_password],  # Django'ning parol qoidalari (settings.py'dagi)
    )
    password2 = serializers.CharField(write_only=True, label='Parolni tasdiqlang')

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2')

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError(
                {'password2': 'Parollar bir xil emas.'}
            )
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        # create_user() parolni HASH qilib saqlaydi, User.objects.create() esa ochiq matnda!
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Foydalanuvchi ma'lumotlarini ko'rsatish uchun (parolsiz!)"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_of_birth', 'date_joined')
        read_only_fields = ('id', 'date_joined')

from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /auth/register/ — yangi foydalanuvchi yaratish"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    # Global sozlamada IsAuthenticatedOrReadOnly turibdi, lekin ro'yxatdan
    # o'tish uchun login talab qilib bo'lmaydi — shuning uchun ochamiz
    permission_classes = (AllowAny,)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /auth/me/ — o'z profilini ko'rish va tahrirlash"""
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        # URL'dan pk olmaymiz — token kimniki bo'lsa, o'shani qaytaramiz
        return self.request.user

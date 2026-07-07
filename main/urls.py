from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('genres', GenreViewSet)
router.register('singers', SingerViewSet)
router.register('albums', AlbumViewSet)
router.register('songs', SongViewSet)
# queryset atributi yo'q (get_queryset ishlatilgan) — basename qo'lda beriladi
router.register('playlists', PlaylistViewSet, basename='playlist')

urlpatterns = [
    path('', include(router.urls)),
]

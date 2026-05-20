from django.urls import path
from .views import *

urlpatterns = [
    path('singers/', SingerApiView.as_view()),

    path('singers/<int:pk>/', SingerRetrieveUpdateDestroyAPIView.as_view()),

    path('songs/', SongListCreateAPIView.as_view()),

    path('songs/<int:pk>/', SongRetrieveUpdateDestroyAPIView.as_view()),

    path('albums/', AlbumListCreateAPIView.as_view()),

    path('albums/<int:pk>/', AlbumRetrieveUpdateDestroyAPIView.as_view()),
]
# Create your views here.
from django.contrib.admin import actions
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .models import *
from .serializers import *


class SingerViewSet(ModelViewSet):
    queryset = Singer.objects.all()
    serializer_class = SingerSerializer

    def get_serializer_class(self):
        # Action nomlariga qarab to'g'ri serializerlarni qaytaramiz
        if self.action in ['albums', 'add_album']:
            return AlbumSerializer
        return SingerSerializer

    # SHART-1: Qo'shiqchiga tegishli albomlarni chiqarish (GET)
    @action(methods=['get'], detail=True)
    def albums(self, request, pk):
        singer = get_object_or_404(Singer, pk=pk)

        # related_name='albums' orqali qo'shiqchining barcha albomlarini olamiz
        albums = singer.albums.all()
        serializer = AlbumSerializer(albums, many=True)
        return Response(serializer.data)

    # SHART-2: Qo'shiqchiga yangi albom qo'shish (POST)
    @action(methods=['post'], detail=True, url_path='add-album')
    def add_album(self, request, pk):
        singer = get_object_or_404(Singer, pk=pk)

        # Albom ma'lumotlarini validatsiya qilamiz
        serializer = AlbumSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        #  Albomni saqlaymiz va unga ushbu qo'shiqchini (singer) biriktiramiz
        serializer.save(singer=singer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SongViewSet(ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class AlbumViewSet(ModelViewSet):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer

    @action(methods=['get'], detail=True)
    def songs(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        # related_name=songs orqali albumning qo'shiqlarini olamiz.
        songs = album.songs.all()
        serializer = SongSerializer(songs, many=True)
        return Response(serializer.data)

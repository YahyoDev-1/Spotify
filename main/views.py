# Create your views here.
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .models import *
from .serializers import *

class SingerApiView(ListCreateAPIView):
    queryset = Singer.objects.all()
    serializer_class = SingerSerializer

class SingerRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Singer.objects.all()
    serializer_class = SingerSerializer

class SongListCreateAPIView(ListCreateAPIView):
    queryset = Song.objects.all()
    serializer_class = SongSerializer

class SongRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Song.objects.all()
    serializer_class = SongSerializer

class AlbumListCreateAPIView(ListCreateAPIView):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer

class AlbumRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Album.objects.all()
    serializer_class = AlbumSerializer
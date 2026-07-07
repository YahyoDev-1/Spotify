from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .cache import (
    SONGS_TTL,
    GENRES_TTL,
    songs_list_key,
    songs_popular_key,
    genres_list_key,
)
from .models import Genre, Singer, Album, Song, Playlist, PlaylistSong, Like, Follow
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    GenreSerializer,
    SingerSerializer,
    AlbumSerializer,
    SongSerializer,
    PlaylistSerializer,
)


class GenreViewSet(ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    search_fields = ('name',)

    def list(self, request, *args, **kwargs):
        # Cache-aside: avval keshdan qidiramiz
        key = genres_list_key(request.GET.urlencode())
        data = cache.get(key)
        if data is None:
            # Cache miss — bazadan olib, keshga yozib qo'yamiz
            response = super().list(request, *args, **kwargs)
            cache.set(key, response.data, GENRES_TTL)
            return response
        # Cache hit — bazaga umuman bormaymiz
        return Response(data)


class SingerViewSet(ModelViewSet):
    # annotate — obunachilar sonini SQL COUNT bilan hisoblaymiz (har singerga alohida so'rov emas).
    # Diqqat: annotate GROUP BY yasagani uchun Meta.ordering bekor bo'ladi — qo'lda qaytaramiz
    queryset = Singer.objects.annotate(followers_count=Count('followers')).order_by('name')
    serializer_class = SingerSerializer
    search_fields = ('name',)

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

    # POST /singers/{id}/follow/ — obuna, DELETE — obunani bekor qilish
    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def follow(self, request, pk):
        singer = self.get_object()

        if request.method == 'POST':
            # get_or_create — ikkinchi marta bosilsa ham xato bermaydi (idempotent)
            follow, created = Follow.objects.get_or_create(user=request.user, singer=singer)
            if created:
                return Response({'detail': f"{singer.name}ga obuna bo'ldingiz."}, status=status.HTTP_201_CREATED)
            return Response({'detail': 'Siz allaqachon obunasiz.'}, status=status.HTTP_200_OK)

        # DELETE
        deleted, _ = Follow.objects.filter(user=request.user, singer=singer).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Siz bu artistga obuna emassiz.'}, status=status.HTTP_400_BAD_REQUEST)

    # GET /singers/following/ — men obuna bo'lgan artistlar
    @action(methods=['get'], detail=False, permission_classes=(IsAuthenticated,))
    def following(self, request):
        singers = self.get_queryset().filter(followers__user=request.user)
        page = self.paginate_queryset(singers)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class SongViewSet(ModelViewSet):
    # select_related — album, singer va genre'ni bitta so'rovda olish (N+1 muammosini oldini oladi)
    queryset = (
        Song.objects
        .select_related('album', 'album__singer', 'genre')
        .annotate(likes_count=Count('likes'))
        # annotate GROUP BY yasagani uchun Meta.ordering bekor bo'ladi — qo'lda qaytaramiz
        .order_by('album', 'name')
    )
    serializer_class = SongSerializer
    search_fields = ('name',)
    ordering_fields = ('duration', 'name', 'created_at')
    filterset_fields = ('genre', 'album')

    def list(self, request, *args, **kwargs):
        # Cache-aside: kalit ichida querystring bor — har xil qidiruv/filter/sahifa
        # alohida keshlanadi ("?genre=1" bilan "?search=x" aralashib ketmaydi)
        key = songs_list_key(request.GET.urlencode())
        data = cache.get(key)
        if data is None:
            response = super().list(request, *args, **kwargs)
            cache.set(key, response.data, SONGS_TTL)
            return response
        return Response(data)

    # GET /songs/popular/ — eng ko'p like olgan 10 ta qo'shiq
    @action(methods=['get'], detail=False)
    def popular(self, request):
        key = songs_popular_key()
        data = cache.get(key)
        if data is None:
            # Og'ir so'rov: JOIN + COUNT + ORDER — aynan keshlash uchun yaralgan
            songs = self.get_queryset().order_by('-likes_count', 'name')[:10]
            data = self.get_serializer(songs, many=True).data
            cache.set(key, data, SONGS_TTL)
        return Response(data)

    # POST /songs/{id}/like/ — yoqtirish, DELETE — bekor qilish
    @action(
        methods=['post', 'delete'],
        detail=True,
        permission_classes=(IsAuthenticated,),
    )
    def like(self, request, pk):
        song = self.get_object()

        if request.method == 'POST':
            like, created = Like.objects.get_or_create(user=request.user, song=song)
            if created:
                return Response({'detail': 'Qo\'shiq yoqtirilganlarga qo\'shildi.'}, status=status.HTTP_201_CREATED)
            return Response({'detail': 'Siz allaqachon yoqtirgansiz.'}, status=status.HTTP_200_OK)

        # DELETE
        deleted, _ = Like.objects.filter(user=request.user, song=song).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Bu qo\'shiq yoqtirilganlarda yo\'q.'}, status=status.HTTP_400_BAD_REQUEST)

    # GET /songs/liked/ — men yoqtirgan qo'shiqlar
    @action(methods=['get'], detail=False, permission_classes=(IsAuthenticated,))
    def liked(self, request):
        songs = self.get_queryset().filter(likes__user=request.user)
        page = self.paginate_queryset(songs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class AlbumViewSet(ModelViewSet):
    queryset = Album.objects.select_related('singer')
    serializer_class = AlbumSerializer
    search_fields = ('name',)
    filterset_fields = ('singer',)

    def get_serializer_class(self):
        if self.action in ['songs', 'add_song']:
            return SongSerializer
        return AlbumSerializer

    @action(methods=['get'], detail=True)
    def songs(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        # SongSerializer likes_count kutadi — shuning uchun bu yerda ham annotate qilamiz
        songs = (
            album.songs
            .select_related('album', 'genre')
            .annotate(likes_count=Count('likes'))
        )
        serializer = SongSerializer(songs, many=True)
        return Response(serializer.data)


class PlaylistViewSet(ModelViewSet):
    serializer_class = PlaylistSerializer
    # Global qoida ustiga object-level tekshiruv qo'shamiz
    permission_classes = (IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly)
    search_fields = ('name',)

    def get_queryset(self):
        # Yopiq (is_public=False) playlistlar faqat egasiga ko'rinadi.
        # Bu XAVFSIZLIK filtri: begona odam uchun yopiq playlist "mavjud emas" (404)
        queryset = (
            Playlist.objects
            .select_related('user')
            .prefetch_related('playlist_songs__song__album')
        )
        if self.request.user.is_authenticated:
            return queryset.filter(Q(is_public=True) | Q(user=self.request.user))
        return queryset.filter(is_public=True)

    def perform_create(self, serializer):
        # Egasini KLIENT emas, TOKEN belgilaydi — soxtalashtirib bo'lmaydi
        serializer.save(user=self.request.user)

    # POST /playlists/{id}/add-song/  {"song_id": 5, "order": 3}
    @action(methods=['post'], detail=True, url_path='add-song')
    def add_song(self, request, pk):
        # self.get_object() — get_queryset + IsOwnerOrReadOnly'dan o'tadi...
        playlist = self.get_object()
        # ...lekin bu GET emas, o'zgartirish — egaligini qo'lda tekshiramiz
        if playlist.user != request.user:
            return Response(
                {'detail': 'Faqat o\'z playlistingizga qo\'shiq qo\'sha olasiz.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        song = get_object_or_404(Song, pk=request.data.get('song_id'))

        # Tartib berilmasa — oxiriga qo'shamiz
        order = request.data.get('order')
        if order is None:
            last = playlist.playlist_songs.order_by('-order').first()
            order = (last.order + 1) if last else 1

        playlist_song, created = PlaylistSong.objects.get_or_create(
            playlist=playlist, song=song, defaults={'order': order},
        )
        if not created:
            return Response(
                {'detail': 'Bu qo\'shiq playlistda allaqachon bor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # get_object() prefetch keshi o'zgarishdan OLDINGI holatni saqlab qolgan —
        # yangilangan ro'yxatni ko'rsatish uchun obyektni qayta o'qiymiz
        playlist = self.get_object()
        return Response(self.get_serializer(playlist).data, status=status.HTTP_201_CREATED)

    # POST /playlists/{id}/remove-song/  {"song_id": 5}
    @action(methods=['post'], detail=True, url_path='remove-song')
    def remove_song(self, request, pk):
        playlist = self.get_object()
        if playlist.user != request.user:
            return Response(
                {'detail': 'Faqat o\'z playlistingizdan qo\'shiq o\'chira olasiz.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        deleted, _ = playlist.playlist_songs.filter(song_id=request.data.get('song_id')).delete()
        if not deleted:
            return Response(
                {'detail': 'Bu qo\'shiq playlistda yo\'q.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Prefetch keshi eskirgan — yangilangan holatni qayta o'qiymiz
        playlist = self.get_object()
        return Response(self.get_serializer(playlist).data, status=status.HTTP_200_OK)

    # GET /playlists/my/ — faqat mening playlistlarim (yopiqlari bilan)
    @action(methods=['get'], detail=False, permission_classes=(IsAuthenticated,))
    def my(self, request):
        playlists = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(playlists)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

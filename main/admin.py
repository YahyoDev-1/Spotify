from django.contrib import admin

from .models import Genre, Singer, Album, Song, Playlist, PlaylistSong, Like, Follow


class PlaylistSongInline(admin.TabularInline):
    """Playlist sahifasida qo'shiqlarni tartibi bilan ko'rsatish"""
    model = PlaylistSong
    extra = 1


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public', 'created_at')
    list_filter = ('is_public',)
    search_fields = ('name', 'user__username')
    inlines = [PlaylistSongInline]


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('name', 'album', 'genre', 'get_duration_display')
    list_filter = ('genre',)
    search_fields = ('name',)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('name', 'singer', 'release_date')
    search_fields = ('name', 'singer__name')


@admin.register(Singer)
class SingerAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    search_fields = ('name',)


admin.site.register(Genre)
admin.site.register(Like)
admin.site.register(Follow)

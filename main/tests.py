import datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Genre, Singer, Album, Song, Playlist, PlaylistSong, Like, Follow

User = get_user_model()


class CatalogFixtureMixin:
    """Barcha test klasslar uchun umumiy boshlang'ich ma'lumotlar.

    setUpTestData — klass uchun BIR MARTA ishlaydi (har testdan oldin emas),
    shuning uchun setUp'dan ancha tez. Django har testga obyektlarning
    izolyatsiya qilingan nusxasini beradi.
    """

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username='yahyobek', email='y@test.com', password='SuperSecret123!',
        )
        cls.other = User.objects.create_user(
            username='ali', email='ali@test.com', password='AliSecret123!',
        )
        cls.genre = Genre.objects.create(name='Klassika')
        cls.singer = Singer.objects.create(name='Sherali Jorayev')
        cls.album = Album.objects.create(
            name='Bandaman', singer=cls.singer, release_date=datetime.date(1995, 5, 1),
        )
        cls.song1 = Song.objects.create(
            name='Bandaman', genre=cls.genre, album=cls.album,
            duration=datetime.timedelta(minutes=5),
        )
        cls.song2 = Song.objects.create(
            name="O'zbegim", genre=cls.genre, album=cls.album,
            duration=datetime.timedelta(minutes=6),
        )

    def setUp(self):
        cache.clear()  # throttle hisobchilari testlar orasida yig'ilib qolmasin


class CatalogTests(CatalogFixtureMixin, APITestCase):
    """Katalog: o'qish hammaga, yozish faqat login qilganlarga"""

    def test_anonymous_can_read_songs(self):
        response = self.client.get('/songs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], 2)

    def test_anonymous_cannot_create_singer(self):
        response = self.client.post('/singers/', {'name': 'Yangi Artist'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_can_create_singer(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post('/singers/', {'name': 'Yangi Artist', 'country': 'UZ'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Singer.objects.filter(name='Yangi Artist').exists())

    def test_songs_filter_by_genre(self):
        rock = Genre.objects.create(name='Rock')
        Song.objects.create(
            name='Rock qoshiq', genre=rock, album=self.album,
            duration=datetime.timedelta(minutes=3),
        )

        response = self.client.get(f'/songs/?genre={rock.id}')

        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['name'], 'Rock qoshiq')


class PlaylistTests(CatalogFixtureMixin, APITestCase):
    """Playlist: egalik, maxfiylik va qo'shiq boshqaruvi"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.public_pl = Playlist.objects.create(name='Ochiq playlist', user=cls.owner, is_public=True)
        cls.private_pl = Playlist.objects.create(name='Yopiq playlist', user=cls.owner, is_public=False)

    def test_owner_comes_from_token_not_payload(self):
        """Klient 'user' yuborsa ham, ega tokendan olinadi"""
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            '/playlists/', {'name': 'Yangi', 'is_public': True, 'user': self.other.id},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['user'], 'yahyobek')

    def test_private_playlist_hidden_from_others(self):
        """Begonaga yopiq playlist 404 (403 emas — mavjudligi ham sir)"""
        self.client.force_authenticate(user=self.other)

        list_response = self.client.get('/playlists/')
        detail_response = self.client.get(f'/playlists/{self.private_pl.id}/')

        names = [p['name'] for p in list_response.json()['results']]
        self.assertNotIn('Yopiq playlist', names)
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_sees_own_private_playlist(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(f'/playlists/{self.private_pl.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_cannot_modify_playlist(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(f'/playlists/{self.public_pl.id}/', {'name': 'Vayron'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_song_with_auto_order(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(f'/playlists/{self.public_pl.id}/add-song/', {'song_id': self.song1.id})
        response = self.client.post(f'/playlists/{self.public_pl.id}/add-song/', {'song_id': self.song2.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        orders = [(ps['song']['name'], ps['order']) for ps in response.json()['songs']]
        self.assertEqual(orders, [('Bandaman', 1), ("O'zbegim", 2)])

    def test_add_duplicate_song_rejected(self):
        self.client.force_authenticate(user=self.owner)
        PlaylistSong.objects.create(playlist=self.public_pl, song=self.song1, order=1)

        response = self.client.post(f'/playlists/{self.public_pl.id}/add-song/', {'song_id': self.song1.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_cannot_add_song_to_foreign_playlist(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(f'/playlists/{self.public_pl.id}/add-song/', {'song_id': self.song1.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_song(self):
        self.client.force_authenticate(user=self.owner)
        PlaylistSong.objects.create(playlist=self.public_pl, song=self.song1, order=1)

        response = self.client.post(
            f'/playlists/{self.public_pl.id}/remove-song/', {'song_id': self.song1.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.public_pl.playlist_songs.count(), 0)

    def test_my_returns_all_own_playlists(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get('/playlists/my/')

        names = {p['name'] for p in response.json()['results']}
        self.assertEqual(names, {'Ochiq playlist', 'Yopiq playlist'})


class LikeTests(CatalogFixtureMixin, APITestCase):
    """Like/unlike oqimi"""

    def test_like_flow(self):
        self.client.force_authenticate(user=self.other)
        url = f'/songs/{self.song1.id}/like/'

        first = self.client.post(url)
        second = self.client.post(url)  # idempotent: xato emas

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.filter(song=self.song1).count(), 1)

    def test_likes_count_in_song_list(self):
        Like.objects.create(user=self.owner, song=self.song1)
        Like.objects.create(user=self.other, song=self.song1)

        response = self.client.get('/songs/')

        song = next(s for s in response.json()['results'] if s['id'] == self.song1.id)
        self.assertEqual(song['likes_count'], 2)

    def test_unlike_flow(self):
        self.client.force_authenticate(user=self.other)
        Like.objects.create(user=self.other, song=self.song1)
        url = f'/songs/{self.song1.id}/like/'

        first = self.client.delete(url)
        second = self.client.delete(url)  # ikkinchi marta: yoqtirilganlarda yo'q

        self.assertEqual(first.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_cannot_like(self):
        response = self.client.post(f'/songs/{self.song1.id}/like/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_liked_list_shows_only_own_likes(self):
        Like.objects.create(user=self.other, song=self.song1)
        Like.objects.create(user=self.owner, song=self.song2)  # begonaniki
        self.client.force_authenticate(user=self.other)

        response = self.client.get('/songs/liked/')

        names = [s['name'] for s in response.json()['results']]
        self.assertEqual(names, ['Bandaman'])


class FollowTests(CatalogFixtureMixin, APITestCase):
    """Follow/unfollow oqimi"""

    def test_follow_flow(self):
        self.client.force_authenticate(user=self.other)
        url = f'/singers/{self.singer.id}/follow/'

        first = self.client.post(url)
        second = self.client.post(url)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(self.singer.followers.count(), 1)

    def test_followers_count_in_singer_list(self):
        Follow.objects.create(user=self.owner, singer=self.singer)
        Follow.objects.create(user=self.other, singer=self.singer)

        response = self.client.get('/singers/')

        singer = next(s for s in response.json()['results'] if s['id'] == self.singer.id)
        self.assertEqual(singer['followers_count'], 2)

    def test_unfollow(self):
        self.client.force_authenticate(user=self.other)
        Follow.objects.create(user=self.other, singer=self.singer)

        response = self.client.delete(f'/singers/{self.singer.id}/follow/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.singer.followers.count(), 0)

    def test_following_list(self):
        Follow.objects.create(user=self.other, singer=self.singer)
        self.client.force_authenticate(user=self.other)

        response = self.client.get('/singers/following/')

        names = [s['name'] for s in response.json()['results']]
        self.assertEqual(names, ['Sherali Jorayev'])


class CacheTests(CatalogFixtureMixin, APITestCase):
    """Cache-aside va invalidatsiya stsenariylari"""

    def test_song_list_served_from_cache(self):
        """Ikkinchi so'rov keshdan keladi — bazadagi 'yashirin' o'zgarishni ko'rmaydi"""
        self.client.get('/songs/')  # keshni to'ldiramiz

        # queryset.update() signal YUBORMAYDI — kesh bexabar qoladi.
        # Bu keshdan o'qilayotganini isbotlash uchun ataylab qilingan hiyla.
        Song.objects.filter(id=self.song1.id).update(name='Yashirin nom')

        response = self.client.get('/songs/')

        names = [s['name'] for s in response.json()['results']]
        self.assertIn('Bandaman', names)  # hali ham eski nom — demak keshdan!
        self.assertNotIn('Yashirin nom', names)

    def test_new_song_invalidates_cache(self):
        """create() signal orqali versiyani oshiradi — ro'yxat yangilanadi"""
        self.client.get('/songs/')  # keshni to'ldiramiz

        Song.objects.create(
            name='Yangi qoshiq', genre=self.genre, album=self.album,
            duration=datetime.timedelta(minutes=4),
        )

        response = self.client.get('/songs/')

        self.assertEqual(response.json()['count'], 3)  # yangi qo'shiq ko'rindi

    def test_like_invalidates_song_cache(self):
        """Like bosilsa likes_count keshda eskirib qolmasligi kerak"""
        self.client.get('/songs/')  # keshda likes_count=0

        Like.objects.create(user=self.other, song=self.song1)

        response = self.client.get('/songs/')

        song = next(s for s in response.json()['results'] if s['id'] == self.song1.id)
        self.assertEqual(song['likes_count'], 1)

    def test_popular_returns_most_liked_first(self):
        Like.objects.create(user=self.owner, song=self.song2)
        Like.objects.create(user=self.other, song=self.song2)
        Like.objects.create(user=self.owner, song=self.song1)

        response = self.client.get('/songs/popular/')

        names = [s['name'] for s in response.json()]
        self.assertEqual(names[0], "O'zbegim")  # 2 like — birinchi o'rinda
        self.assertEqual(names[1], 'Bandaman')

    def test_genre_list_cache_invalidated_on_create(self):
        self.client.get('/genres/')  # keshni to'ldiramiz

        Genre.objects.create(name='Jazz')

        response = self.client.get('/genres/')

        names = [g['name'] for g in response.json()['results']]
        self.assertIn('Jazz', names)

    def test_different_querystrings_cached_separately(self):
        """?genre=X filtri "hammasi" keshiga aralashib ketmasligi kerak"""
        rock = Genre.objects.create(name='Rock')
        Song.objects.create(
            name='Rock qoshiq', genre=rock, album=self.album,
            duration=datetime.timedelta(minutes=3),
        )

        all_response = self.client.get('/songs/')
        filtered_response = self.client.get(f'/songs/?genre={rock.id}')

        self.assertEqual(all_response.json()['count'], 3)
        self.assertEqual(filtered_response.json()['count'], 1)

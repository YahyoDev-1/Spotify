"""Kesh kalitlari va invalidatsiya yordamchilari.

Invalidatsiya usuli — "versiyalangan kalit":
har bir ro'yxat kaliti ichida versiya raqami bor (masalan songs:list:v3:...).
Ma'lumot o'zgarganda versiyani +1 qilamiz — barcha eski kalitlar bir zumda
"yetim" bo'lib qoladi (ularni hech kim so'ramaydi) va TTL bilan o'zi o'chadi.
Bitta-bitta kalit qidirib o'chirishga hojat yo'q.
"""
from django.core.cache import cache

SONGS_VERSION_KEY = 'songs:version'
GENRES_VERSION_KEY = 'genres:version'

# TTL — keshdagi yozuvning yashash muddati (sekundlarda)
SONGS_TTL = 5 * 60       # qo'shiqlar tez-tez o'zgaradi
GENRES_TTL = 60 * 60     # janrlar deyarli o'zgarmaydi


def get_version(version_key):
    """Joriy versiya raqamini olish (birinchi murojaatda 1 deb boshlaymiz)"""
    version = cache.get(version_key)
    if version is None:
        version = 1
        cache.set(version_key, version, None)  # None = muddatsiz saqlanadi
    return version


def bump_version(version_key):
    """Versiyani oshirish = shu turkumdagi BARCHA keshni bekor qilish"""
    try:
        cache.incr(version_key)
    except ValueError:
        # Kalit hali yo'q (yoki kesh tozalangan) — 2 dan boshlaymiz
        cache.set(version_key, 2, None)


def songs_list_key(querystring):
    """Har xil filter/qidiruv/sahifa — har xil kalit"""
    version = get_version(SONGS_VERSION_KEY)
    return f'songs:list:v{version}:{querystring or "all"}'


def songs_popular_key():
    version = get_version(SONGS_VERSION_KEY)
    return f'songs:popular:v{version}'


def genres_list_key(querystring):
    version = get_version(GENRES_VERSION_KEY)
    return f'genres:list:v{version}:{querystring or "all"}'

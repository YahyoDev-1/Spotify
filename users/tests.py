from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterTests(APITestCase):
    """POST /auth/register/ stsenariylari"""

    url = '/auth/register/'

    def setUp(self):
        # Throttle hisobchilari keshda yashaydi va testlar orasida O'ZI tozalanmaydi
        # (baza rollback bo'ladi, kesh esa yo'q!) — qo'lda tozalaymiz
        cache.clear()

    def test_register_success(self):
        data = {
            'username': 'yangi_user',
            'email': 'yangi@test.com',
            'password': 'KuchliParol123!',
            'password2': 'KuchliParol123!',
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Parol javobda KO'RINMASLIGI kerak (write_only)
        self.assertNotIn('password', response.json())
        # Parol bazada HASH holida bo'lishi kerak, ochiq matn emas
        user = User.objects.get(username='yangi_user')
        self.assertNotEqual(user.password, 'KuchliParol123!')
        self.assertTrue(user.check_password('KuchliParol123!'))

    def test_register_weak_password_rejected(self):
        data = {
            'username': 'user2',
            'email': 'u2@test.com',
            'password': '123',
            'password2': '123',
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)  # foydalanuvchi yaratilmadi

    def test_register_password_mismatch_rejected(self):
        data = {
            'username': 'user3',
            'email': 'u3@test.com',
            'password': 'KuchliParol123!',
            'password2': 'BoshqaParol123!',
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.json())

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(username='bor_user', email='band@test.com', password='Parol12345!')
        data = {
            'username': 'boshqa_user',
            'email': 'band@test.com',  # allaqachon band
            'password': 'KuchliParol123!',
            'password2': 'KuchliParol123!',
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    """POST /auth/login/ va /auth/refresh/ stsenariylari"""

    url = '/auth/login/'

    def setUp(self):
        cache.clear()  # login throttle 5/min — har test toza boshlansin
        self.user = User.objects.create_user(
            username='yahyobek', email='y@test.com', password='SuperSecret123!',
        )

    def test_login_returns_token_pair(self):
        response = self.client.post(self.url, {'username': 'yahyobek', 'password': 'SuperSecret123!'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())

    def test_login_wrong_password_rejected(self):
        response = self.client.post(self.url, {'username': 'yahyobek', 'password': 'notogri'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_works_on_protected_endpoint(self):
        access = self.client.post(
            self.url, {'username': 'yahyobek', 'password': 'SuperSecret123!'},
        ).json()['access']

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access)
        response = self.client.get('/auth/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['username'], 'yahyobek')

    def test_refresh_returns_new_access(self):
        refresh = self.client.post(
            self.url, {'username': 'yahyobek', 'password': 'SuperSecret123!'},
        ).json()['refresh']

        response = self.client.post('/auth/refresh/', {'refresh': refresh})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())

    def test_login_throttled_after_five_attempts(self):
        """Brute-force himoyasi: 6-urinish 429 qaytarishi shart"""
        for i in range(5):
            self.client.post(self.url, {'username': 'yahyobek', 'password': f'xato-{i}'})

        response = self.client.post(self.url, {'username': 'yahyobek', 'password': 'xato-6'})

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Retry-After', response.headers)


class MeTests(APITestCase):
    """GET/PATCH /auth/me/ stsenariylari"""

    url = '/auth/me/'

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='yahyobek', email='y@test.com', password='SuperSecret123!',
        )

    def test_me_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_own_profile(self):
        # force_authenticate — JWT bosqichini chetlab, to'g'ridan-to'g'ri shu user sifatida kiramiz.
        # Login oqimini alohida testlar tekshiradi; bu yerda faqat view mantiqi kerak.
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['email'], 'y@test.com')

    def test_me_patch_updates_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.url, {'first_name': 'Yahyobek', 'date_of_birth': '2005-03-15'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Yahyobek')
        self.assertEqual(str(self.user.date_of_birth), '2005-03-15')

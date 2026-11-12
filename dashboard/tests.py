from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from halaqat.models import Halaqa


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            phone='0500000000',
            password='AdminPassword123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_ADMIN
        )
        self.regular_user = User.objects.create_user(
            username='student_reg',
            email='reg@example.com',
            phone='0500000001',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_STUDENT
        )

    def test_regular_user_cannot_access_dashboard(self):
        self.client.login(username='student_reg', password='Password123!')
        response = self.client.get(reverse('dashboard:overview'))
        self.assertNotEqual(response.status_code, 200)

    def test_admin_can_access_dashboard_and_suspend_user(self):
        self.client.login(username='admin_boss', password='AdminPassword123!')
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, 200)

        # Suspend regular user
        suspend_url = reverse('dashboard:toggle_user_suspend', kwargs={'pk': self.regular_user.id})
        response = self.client.post(suspend_url)
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_suspended)

        # Reactivate
        response = self.client.post(suspend_url)
        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_suspended)

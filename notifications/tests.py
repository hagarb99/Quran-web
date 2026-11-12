from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from .models import Notification, notify_user


class NotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='user_notif',
            email='notif@example.com',
            phone='0512345678',
            password='Password123!',
            gender=User.GENDER_MALE
        )
        self.actor = User.objects.create_user(
            username='user_sender',
            email='sender@example.com',
            phone='0587654321',
            password='Password123!',
            gender=User.GENDER_MALE
        )

    def test_notification_creation_and_mark_as_read(self):
        notif = notify_user(
            recipient=self.user,
            actor=self.actor,
            title='تنبيه تجريبي',
            message='هذا إشعار للتجربة',
            link='/halaqat/browse/',
            notification_type=Notification.TYPE_GENERAL
        )
        self.assertIsNotNone(notif)
        self.assertFalse(notif.is_read)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 1)

        # Access notification via read-and-redirect
        self.client.login(username='user_notif', password='Password123!')
        url = reverse('notifications:read_and_redirect', kwargs={'pk': notif.id})
        response = self.client.get(url)
        self.assertRedirects(response, '/halaqat/browse/')

        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)

    def test_mark_all_read(self):
        notify_user(recipient=self.user, title='إشعار 1', message='رسالة 1')
        notify_user(recipient=self.user, title='إشعار 2', message='رسالة 2')
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 2)

        self.client.login(username='user_notif', password='Password123!')
        self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)

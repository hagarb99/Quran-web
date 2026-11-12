from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import time, timedelta
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember
from .models import Session


class SessionLifecycleAndBusinessRulesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher_session',
            email='ts@example.com',
            phone='0566666666',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_TEACHER
        )
        self.halaqa = Halaqa.objects.create(
            name='حلقة التجويد',
            gender=Halaqa.GENDER_MALE,
            visibility=Halaqa.VISIBILITY_PUBLIC,
            owner=self.teacher
        )
        HalaqaMember.objects.create(
            halaqa=self.halaqa,
            user=self.teacher,
            role=HalaqaMember.ROLE_OWNER
        )

    def test_session_lifecycle(self):
        """
        Rule 1: Sessions are created manually.
        Rule 5: Cancelled sessions cannot be completed.
        Rule 6 & 7: Completed sessions can be reopened; they become IN_PROGRESS.
        """
        session = Session.objects.create(
            halaqa=self.halaqa,
            title='جلسة حفظ سورة الكهف',
            date=timezone.now().date(),
            start_time=time(16, 0),
            created_by=self.teacher
        )
        self.assertEqual(session.status, Session.STATUS_SCHEDULED)

        # Start session
        session.status = Session.STATUS_IN_PROGRESS
        session.save()
        self.assertEqual(session.status, Session.STATUS_IN_PROGRESS)

        # Mark completed
        session.mark_completed(self.teacher)
        self.assertEqual(session.status, Session.STATUS_COMPLETED)
        self.assertIsNotNone(session.completed_at)
        self.assertEqual(session.completed_by, self.teacher)

        # Reopen completed session
        session.reopen(self.teacher)
        self.assertEqual(session.status, Session.STATUS_IN_PROGRESS)
        self.assertIsNotNone(session.reopened_at)
        self.assertEqual(session.reopened_by, self.teacher)

        # Cancel session
        session.cancel(self.teacher)
        self.assertEqual(session.status, Session.STATUS_CANCELLED)

        # Rule 5: Cancelled sessions cannot be completed
        with self.assertRaises(ValueError):
            session.mark_completed(self.teacher)

    def test_soft_delete_session(self):
        """Rule 10: Use soft deletion for sessions rather than permanent deletion."""
        session = Session.objects.create(
            halaqa=self.halaqa,
            title='جلسة اختبار تجويد',
            date=timezone.now().date(),
            start_time=time(18, 0),
            created_by=self.teacher
        )
        self.assertEqual(Session.objects.count(), 1)

        session.soft_delete(self.teacher)
        # Default objects manager excludes soft-deleted
        self.assertEqual(Session.objects.count(), 0)
        # all_objects includes soft-deleted for audit
        self.assertEqual(Session.all_objects.count(), 1)
        self.assertTrue(session.is_deleted)
        self.assertEqual(session.deleted_by, self.teacher)

    def test_start_session_notifies_students(self):
        """Verify that starting a session sends live notifications to enrolled students."""
        from notifications.models import Notification
        student = User.objects.create_user(
            username='student_notify',
            email='sn@example.com',
            phone='0577777777',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_STUDENT,
            first_name='حمزة'
        )
        HalaqaMember.objects.create(halaqa=self.halaqa, user=student, role=HalaqaMember.ROLE_STUDENT)

        session = Session.objects.create(
            halaqa=self.halaqa,
            title='جلسة الفجر المباشرة',
            date=timezone.now().date(),
            start_time=time(5, 30),
            meet_url='https://meet.google.com/abc-defg-hij',
            created_by=self.teacher
        )

        self.client.login(username='teacher_session', password='Password123!')
        url = reverse('halaqa_sessions:action', kwargs={'pk': session.id, 'action': 'start'})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        session.refresh_from_db()
        self.assertEqual(session.status, Session.STATUS_IN_PROGRESS)

        # Student must have received the live start notification
        notif = Notification.objects.filter(recipient=student, notification_type=Notification.TYPE_SESSION_STARTED).first()
        self.assertIsNotNone(notif)
        self.assertIn('بدأت الجلسة الآن', notif.title)
        self.assertIn('Google Meet', notif.message)

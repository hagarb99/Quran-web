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

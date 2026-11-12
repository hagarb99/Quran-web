from django.test import TestCase
from django.utils import timezone
from datetime import time
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember
from halaqa_sessions.models import Session
from .models import Attendance


class AttendanceTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher_att',
            email='att_t@example.com',
            phone='0577777771',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(
            username='student_att',
            email='att_s@example.com',
            phone='0577777772',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_STUDENT
        )
        self.halaqa = Halaqa.objects.create(
            name='حلقة التسميع المسائي',
            gender=Halaqa.GENDER_MALE,
            owner=self.teacher
        )
        HalaqaMember.objects.create(halaqa=self.halaqa, user=self.teacher, role=HalaqaMember.ROLE_OWNER)
        HalaqaMember.objects.create(halaqa=self.halaqa, user=self.student, role=HalaqaMember.ROLE_STUDENT)

        self.session = Session.objects.create(
            halaqa=self.halaqa,
            title='جلسة رقم 1',
            date=timezone.now().date(),
            start_time=time(17, 0),
            created_by=self.teacher
        )

    def test_record_attendance_and_soft_delete(self):
        att = Attendance.objects.create(
            session=self.session,
            student=self.student,
            status=Attendance.STATUS_PRESENT,
            notes='حضر في الموعد تماماً',
            created_by=self.teacher
        )
        self.assertEqual(Attendance.objects.filter(student=self.student).count(), 1)

        # Soft delete
        att.soft_delete(self.teacher)
        self.assertEqual(Attendance.objects.filter(student=self.student).count(), 0)
        self.assertEqual(Attendance.all_objects.filter(student=self.student).count(), 1)
        self.assertTrue(att.is_deleted)
        self.assertEqual(att.deleted_by, self.teacher)

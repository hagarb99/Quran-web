from django.test import TestCase
from django.utils import timezone
from datetime import time
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember
from halaqa_sessions.models import Session
from .models import Recitation


class RecitationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher_rec',
            email='rec_t@example.com',
            phone='0588888881',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(
            username='student_rec',
            email='rec_s@example.com',
            phone='0588888882',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_STUDENT
        )
        self.halaqa = Halaqa.objects.create(
            name='حلقة الإتقان',
            gender=Halaqa.GENDER_MALE,
            owner=self.teacher
        )
        HalaqaMember.objects.create(halaqa=self.halaqa, user=self.teacher, role=HalaqaMember.ROLE_OWNER)
        HalaqaMember.objects.create(halaqa=self.halaqa, user=self.student, role=HalaqaMember.ROLE_STUDENT)

        self.session = Session.objects.create(
            halaqa=self.halaqa,
            title='جلسة تسميع جزء تبارك',
            date=timezone.now().date(),
            start_time=time(19, 0),
            created_by=self.teacher
        )

    def test_recitation_performance_rating_levels(self):
        """
        Important: Use performance levels only. Do not implement star ratings.
        """
        rec = Recitation.objects.create(
            session=self.session,
            student=self.student,
            new_memorization='سورة الملك من 1 إلى 15',
            near_revision='سورة القلم كاملة',
            far_revision='جزء عم كاملاً',
            rating=Recitation.RATING_MUMTAZ,
            teacher_notes='قراءة متقنة ومخارج صحيحة',
            next_assignment='حفظ سورة الملك من 16 إلى 30',
            created_by=self.teacher
        )
        self.assertEqual(rec.rating, 'MUMTAZ')
        self.assertEqual(rec.get_rating_display(), 'ممتاز')

        # Test soft delete
        rec.soft_delete(self.teacher)
        self.assertEqual(Recitation.objects.filter(student=self.student).count(), 0)
        self.assertEqual(Recitation.all_objects.filter(student=self.student).count(), 1)

from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from accounts.models import User
from .models import Halaqa, HalaqaMember, JoinRequest
from chat.models import Conversation


class HalaqatBusinessRulesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher_male = User.objects.create_user(
            username='teacher_m',
            email='tm@example.com',
            phone='0511111111',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_TEACHER,
            first_name='الشيخ أحمد'
        )
        self.student_male = User.objects.create_user(
            username='student_m',
            email='sm@example.com',
            phone='0522222222',
            password='Password123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_STUDENT,
            first_name='يوسف'
        )
        self.student_female = User.objects.create_user(
            username='student_f',
            email='sf@example.com',
            phone='0533333333',
            password='Password123!',
            gender=User.GENDER_FEMALE,
            role=User.ROLE_STUDENT,
            first_name='فاطمة'
        )

        # Create a male public halaqa
        self.halaqa_male = Halaqa.objects.create(
            name='حلقة الفجر للرجال',
            description='حلقة حفظ ومراجعة للذكور',
            gender=Halaqa.GENDER_MALE,
            visibility=Halaqa.VISIBILITY_PUBLIC,
            owner=self.teacher_male
        )
        HalaqaMember.objects.create(
            halaqa=self.halaqa_male,
            user=self.teacher_male,
            role=HalaqaMember.ROLE_OWNER
        )
        Conversation.objects.create(
            halaqa=self.halaqa_male,
            chat_type=Conversation.TYPE_GROUP
        )

        # Create a private female halaqa
        self.halaqa_female_private = Halaqa.objects.create(
            name='حلقة الهدى الخاصة للنساء',
            description='حلقة خاصة',
            gender=Halaqa.GENDER_FEMALE,
            visibility=Halaqa.VISIBILITY_PRIVATE,
            owner=self.teacher_male
        )
        HalaqaMember.objects.create(
            halaqa=self.halaqa_female_private,
            user=self.teacher_male,
            role=HalaqaMember.ROLE_OWNER
        )

    def test_gender_restriction_on_membership(self):
        """Rule 8: Students can only join Halaqat matching their gender."""
        # Male student can join male halaqa
        member_m = HalaqaMember(
            halaqa=self.halaqa_male,
            user=self.student_male,
            role=HalaqaMember.ROLE_STUDENT
        )
        member_m.full_clean()
        member_m.save()
        self.assertTrue(HalaqaMember.objects.filter(halaqa=self.halaqa_male, user=self.student_male).exists())

        # Female student CANNOT join male halaqa
        member_f = HalaqaMember(
            halaqa=self.halaqa_male,
            user=self.student_female,
            role=HalaqaMember.ROLE_STUDENT
        )
        with self.assertRaises(ValidationError):
            member_f.full_clean()

    def test_teachers_can_manage_any_gender_halaqa(self):
        """Rule 9: Teachers and assistants can manage both male and female Halaqat."""
        # Male teacher is already owner of female private halaqa
        member_teacher = HalaqaMember.objects.filter(halaqa=self.halaqa_female_private, user=self.teacher_male).first()
        self.assertIsNotNone(member_teacher)
        # Should clean without validation error because role is OWNER/TEACHER, not STUDENT
        member_teacher.full_clean()

    def test_private_halaqa_not_in_public_browse(self):
        """Rule 6: Private Halaqat must not appear in public browsing."""
        self.client.login(username='student_f', password='Password123!')
        response = self.client.get(reverse('halaqat:browse_public'))
        self.assertContains(response, 'استكشاف الحلقات العامة')
        # Private halaqa should NOT be in context halaqat
        listed_halaqat_ids = [h.id for h in response.context['halaqat']]
        self.assertNotIn(self.halaqa_female_private.id, listed_halaqat_ids)

    def test_join_request_flow(self):
        """Rule 4 & 5: Students can request to join public Halaqat. Owners can approve or reject."""
        self.client.login(username='student_m', password='Password123!')
        # Request to join
        post_url = reverse('halaqat:request_join', kwargs={'pk': self.halaqa_male.id})
        response = self.client.post(post_url, follow=True)
        self.assertTrue(JoinRequest.objects.filter(halaqa=self.halaqa_male, user=self.student_male, status=JoinRequest.STATUS_PENDING).exists())

        # Switch to teacher and approve
        self.client.login(username='teacher_m', password='Password123!')
        req = JoinRequest.objects.get(halaqa=self.halaqa_male, user=self.student_male)
        approve_url = reverse('halaqat:handle_join_request', kwargs={'pk': self.halaqa_male.id, 'req_id': req.id, 'action': 'approve'})
        response = self.client.get(approve_url, follow=True)
        
        req.refresh_from_db()
        self.assertEqual(req.status, JoinRequest.STATUS_APPROVED)
        self.assertTrue(HalaqaMember.objects.filter(halaqa=self.halaqa_male, user=self.student_male, role=HalaqaMember.ROLE_STUDENT).exists())

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember, JoinRequest
from subscriptions.models import (
    Subscription,
    StudentSubscriptionProfile,
    Payment,
    SubscriptionAuditLog
)
from subscriptions.services import (
    get_user_subscription_status,
    has_active_access,
    get_teacher_unique_students,
    recalculate_teacher_allocations,
    assign_student_to_teacher,
    transfer_student_to_independent,
    activate_subscription,
    renew_subscription,
    pause_subscription,
    close_subscription
)


class SubscriptionsPlatformTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()

        # 1. Platform Admin
        self.admin = User.objects.create_user(
            username='admin_boss',
            email='admin@example.com',
            phone='0500000001',
            password='AdminPassword123!',
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True
        )

        # 2. Teacher 1 (Ahmed)
        self.teacher_ahmed = User.objects.create_user(
            username='teacher_ahmed',
            email='ahmed@example.com',
            phone='0500000002',
            password='Password123!',
            role=User.ROLE_TEACHER,
            first_name='أحمد'
        )

        # 3. Teacher 2 (Mahmoud)
        self.teacher_mahmoud = User.objects.create_user(
            username='teacher_mahmoud',
            email='mahmoud@example.com',
            phone='0500000003',
            password='Password123!',
            role=User.ROLE_TEACHER,
            first_name='محمود'
        )

        # 4. Students
        self.student_1 = User.objects.create_user(
            username='student_1',
            email='s1@example.com',
            phone='0500000011',
            password='Password123!',
            role=User.ROLE_STUDENT,
            first_name='طالب 1'
        )
        self.student_2 = User.objects.create_user(
            username='student_2',
            email='s2@example.com',
            phone='0500000012',
            password='Password123!',
            role=User.ROLE_STUDENT,
            first_name='طالب 2'
        )
        self.student_3 = User.objects.create_user(
            username='student_3',
            email='s3@example.com',
            phone='0500000013',
            password='Password123!',
            role=User.ROLE_STUDENT,
            first_name='طالب 3'
        )

        # 5. Halaqat for Ahmed
        self.halaqa_ahmed_1 = Halaqa.objects.create(
            name='حلقة الفجر',
            gender=Halaqa.GENDER_MALE,
            visibility=Halaqa.VISIBILITY_PUBLIC,
            owner=self.teacher_ahmed
        )
        self.halaqa_ahmed_2 = Halaqa.objects.create(
            name='حلقة النور',
            gender=Halaqa.GENDER_MALE,
            visibility=Halaqa.VISIBILITY_PUBLIC,
            owner=self.teacher_ahmed
        )

    # 1. Platform Admin permissions
    def test_01_platform_admin_full_access(self):
        self.assertTrue(self.admin.is_platform_admin)
        self.assertEqual(get_user_subscription_status(self.admin), Subscription.STATUS_ACTIVE)
        self.assertTrue(has_active_access(self.admin))

    # 2. Teacher access restrictions when pending/expired
    def test_02_teacher_access_restrictions(self):
        self.client.login(username='teacher_ahmed', password='Password123!')
        self.assertEqual(get_user_subscription_status(self.teacher_ahmed), Subscription.STATUS_PENDING)
        self.assertFalse(has_active_access(self.teacher_ahmed))

        # Blocked from creating halaqa
        res = self.client.get(reverse('halaqat:create'), follow=True)
        self.assertRedirects(res, reverse('subscriptions:status_notice'))

    # 3. Student access restrictions when not subscribed
    def test_03_student_access_restrictions(self):
        self.client.login(username='student_1', password='Password123!')
        self.assertEqual(get_user_subscription_status(self.student_1), Subscription.STATUS_PENDING)
        self.assertFalse(has_active_access(self.student_1))

        # Blocked from accessing halaqa detail directly
        res = self.client.get(reverse('halaqat:detail', kwargs={'pk': self.halaqa_ahmed_1.id}), follow=True)
        self.assertRedirects(res, reverse('subscriptions:status_notice'))

    # 4. Unique student counting across multiple Halaqat belonging to same teacher
    def test_04_unique_student_counting_across_multiple_halaqat(self):
        # Student 1 is in both Halaqa 1 and Halaqa 2 of Teacher Ahmed
        HalaqaMember.objects.create(halaqa=self.halaqa_ahmed_1, user=self.student_1, role=HalaqaMember.ROLE_STUDENT)
        HalaqaMember.objects.create(halaqa=self.halaqa_ahmed_2, user=self.student_1, role=HalaqaMember.ROLE_STUDENT)

        # Student 2 is only in Halaqa 1
        HalaqaMember.objects.create(halaqa=self.halaqa_ahmed_1, user=self.student_2, role=HalaqaMember.ROLE_STUDENT)

        unique_students = get_teacher_unique_students(self.teacher_ahmed)
        # Should be 2 unique students (not 3!)
        self.assertEqual(unique_students.count(), 2)

    # 5. Teacher subscription activation & allocation
    def test_05_teacher_subscription_activation(self):
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_TEACHER_WITH_STUDENTS,
            status=Subscription.STATUS_PENDING,
            paid_students_count=2,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        self.assertEqual(get_user_subscription_status(self.teacher_ahmed), Subscription.STATUS_PENDING)

        activate_subscription(sub, actor=self.admin)
        self.teacher_ahmed.refresh_from_db()
        self.assertEqual(get_user_subscription_status(self.teacher_ahmed), Subscription.STATUS_ACTIVE)
        self.assertTrue(has_active_access(self.teacher_ahmed))

    # 6. Automatic dynamic expiration based on end_date
    def test_06_dynamic_subscription_expiration(self):
        past_date = self.now - timedelta(days=2)
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_TEACHER_WITH_STUDENTS,
            status=Subscription.STATUS_ACTIVE,
            paid_students_count=5,
            start_date=past_date - timedelta(days=30),
            end_date=past_date
        )
        # Dynamically returns EXPIRED without cron running
        self.assertEqual(sub.dynamic_status, Subscription.STATUS_EXPIRED)
        self.assertEqual(get_user_subscription_status(self.teacher_ahmed), Subscription.STATUS_EXPIRED)
        self.assertFalse(has_active_access(self.teacher_ahmed))

    # 7. Allocation overflow: 2 paid slots, 3 students (Ahmed adds 2 then 1)
    def test_07_paid_allocation_overflow_new_students_pending(self):
        # Ahmed subscribes for 2 students
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_TEACHER_WITH_STUDENTS,
            status=Subscription.STATUS_ACTIVE,
            paid_students_count=2,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )

        assign_student_to_teacher(self.student_1, self.teacher_ahmed)
        assign_student_to_teacher(self.student_2, self.teacher_ahmed)
        assign_student_to_teacher(self.student_3, self.teacher_ahmed)

        recalculate_teacher_allocations(self.teacher_ahmed)

        # Student 1 & 2 are covered and ACTIVE
        self.assertEqual(get_user_subscription_status(self.student_1), Subscription.STATUS_ACTIVE)
        self.assertEqual(get_user_subscription_status(self.student_2), Subscription.STATUS_ACTIVE)

        # Student 3 is beyond the 2 paid slots -> PENDING!
        self.assertEqual(get_user_subscription_status(self.student_3), Subscription.STATUS_PENDING)

    # 8. Independent Student activation
    def test_08_independent_student_activation(self):
        transfer_student_to_independent(self.student_1, actor=self.admin)
        profile = StudentSubscriptionProfile.objects.get(student=self.student_1)
        self.assertTrue(profile.is_independent)
        self.assertIsNone(profile.teacher)

        # Pending until subscribed
        self.assertEqual(get_user_subscription_status(self.student_1), Subscription.STATUS_PENDING)

        sub = Subscription.objects.create(
            owner=self.student_1,
            subscription_type=Subscription.TYPE_INDEPENDENT_STUDENT,
            status=Subscription.STATUS_ACTIVE,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        self.assertEqual(get_user_subscription_status(self.student_1), Subscription.STATUS_ACTIVE)

    # 9. Individual Teacher subscription without students
    def test_09_individual_teacher_activation(self):
        sub = Subscription.objects.create(
            owner=self.teacher_mahmoud,
            subscription_type=Subscription.TYPE_INDIVIDUAL_TEACHER,
            status=Subscription.STATUS_ACTIVE,
            paid_students_count=0,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        self.assertEqual(get_user_subscription_status(self.teacher_mahmoud), Subscription.STATUS_ACTIVE)
        self.assertTrue(has_active_access(self.teacher_mahmoud))

    # 10. Statuses PENDING, PAUSED, CLOSED, EXPIRED enforcement
    def test_10_status_enforcements(self):
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_INDIVIDUAL_TEACHER,
            status=Subscription.STATUS_ACTIVE,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        self.assertTrue(has_active_access(self.teacher_ahmed))

        pause_subscription(sub, actor=self.admin)
        self.assertFalse(has_active_access(self.teacher_ahmed))
        self.assertEqual(get_user_subscription_status(self.teacher_ahmed), Subscription.STATUS_PAUSED)

        close_subscription(sub, actor=self.admin)
        self.assertFalse(has_active_access(self.teacher_ahmed))
        self.assertEqual(get_user_subscription_status(self.teacher_ahmed), Subscription.STATUS_CLOSED)

    # 11. Public Halaqa browsing is ALWAYS allowed even when restricted
    def test_11_public_halaqa_browsing_allowed_when_restricted(self):
        self.client.login(username='student_1', password='Password123!')
        res = self.client.get(reverse('halaqat:browse_public'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'استكشاف الحلقات العامة')

    # 12. Preventing Halaqa detail access while restricted
    def test_12_prevent_halaqa_detail_access_while_restricted(self):
        self.client.login(username='student_1', password='Password123!')
        res = self.client.get(reverse('halaqat:detail', kwargs={'pk': self.halaqa_ahmed_1.id}), follow=True)
        self.assertRedirects(res, reverse('subscriptions:status_notice'))

    # 13. Preventing join requests while restricted
    def test_13_prevent_join_requests_while_restricted(self):
        self.client.login(username='student_1', password='Password123!')
        res = self.client.post(reverse('halaqat:request_join', kwargs={'pk': self.halaqa_ahmed_1.id}), follow=True)
        self.assertRedirects(res, reverse('subscriptions:status_notice'))

    # 14. Prevent unauthorized cross-teacher student assignment
    def test_14_prevent_cross_teacher_student_assignment(self):
        assign_student_to_teacher(self.student_1, self.teacher_ahmed)
        with self.assertRaises(ValidationError):
            assign_student_to_teacher(self.student_1, self.teacher_mahmoud)

    # 15. Independent student transfer preserves history
    def test_15_transfer_preserves_history(self):
        assign_student_to_teacher(self.student_1, self.teacher_ahmed)
        HalaqaMember.objects.create(halaqa=self.halaqa_ahmed_1, user=self.student_1, role=HalaqaMember.ROLE_STUDENT)

        transfer_student_to_independent(self.student_1, actor=self.admin)

        # Halaqa membership remains preserved
        self.assertTrue(HalaqaMember.objects.filter(halaqa=self.halaqa_ahmed_1, user=self.student_1).exists())
        # Removed from teacher unique students count
        unique_students = get_teacher_unique_students(self.teacher_ahmed)
        self.assertNotIn(self.student_1, unique_students)

    # 16. Individual student restrictions survive Teacher renewal
    def test_16_individual_restriction_survives_teacher_renewal(self):
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_TEACHER_WITH_STUDENTS,
            status=Subscription.STATUS_ACTIVE,
            paid_students_count=10,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        assign_student_to_teacher(self.student_1, self.teacher_ahmed)

        # Admin individually pauses Student 1
        profile = StudentSubscriptionProfile.objects.get(student=self.student_1)
        profile.status_override = StudentSubscriptionProfile.OVERRIDE_PAUSED
        profile.save()

        self.assertEqual(get_user_subscription_status(self.student_1), StudentSubscriptionProfile.OVERRIDE_PAUSED)

        # Teacher renews
        renew_subscription(sub, new_end_date=self.now + timedelta(days=60), actor=self.admin)

        # Student 1 must STILL be PAUSED
        self.assertEqual(get_user_subscription_status(self.student_1), StudentSubscriptionProfile.OVERRIDE_PAUSED)

    # 17. Payment history preservation
    def test_17_payment_history_preservation(self):
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_TEACHER_WITH_STUDENTS,
            status=Subscription.STATUS_ACTIVE,
            paid_students_count=10,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        renew_subscription(
            sub,
            new_end_date=self.now + timedelta(days=60),
            amount=Decimal('450.00'),
            payment_ref='INSTA-12345',
            verified_by=self.admin,
            actor=self.admin,
            notes='تجديد شهر مايو'
        )
        renew_subscription(
            sub,
            new_end_date=self.now + timedelta(days=90),
            amount=Decimal('500.00'),
            payment_ref='INSTA-67890',
            verified_by=self.admin,
            actor=self.admin,
            notes='تجديد شهر يونيو'
        )

        self.assertEqual(sub.payments.count(), 2)
        payments = list(sub.payments.order_by('payment_date'))
        self.assertEqual(payments[0].amount, Decimal('450.00'))
        self.assertEqual(payments[1].amount, Decimal('500.00'))

    # 18. Audit log records actions
    def test_18_audit_logs_recorded(self):
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_INDIVIDUAL_TEACHER,
            status=Subscription.STATUS_PENDING,
            start_date=self.now,
            end_date=self.now + timedelta(days=30)
        )
        activate_subscription(sub, actor=self.admin, notes='تم استلام الدفعة')
        log = SubscriptionAuditLog.objects.filter(target_user=self.teacher_ahmed).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'ACTIVATE_SUBSCRIPTION')
        self.assertEqual(log.actor, self.admin)

    # 19. Unauthorized API access returns 403 JSON
    def test_19_unauthorized_api_returns_403_json(self):
        self.client.login(username='student_1', password='Password123!')
        res = self.client.post(
            reverse('chat:send_message', kwargs={'pk': 1}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()['error'], 'subscription_required')

    # 20. Management Command check_subscriptions updates expired ones
    def test_20_management_command_check_subscriptions(self):
        from django.core.management import call_command
        past_date = self.now - timedelta(days=1)
        sub = Subscription.objects.create(
            owner=self.teacher_ahmed,
            subscription_type=Subscription.TYPE_INDIVIDUAL_TEACHER,
            status=Subscription.STATUS_ACTIVE,
            start_date=past_date - timedelta(days=30),
            end_date=past_date
        )
        call_command('check_subscriptions')
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.STATUS_EXPIRED)

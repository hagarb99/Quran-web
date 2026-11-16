from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from halaqat.models import HalaqaMember
from subscriptions.models import Subscription, StudentSubscriptionProfile
from subscriptions.services import recalculate_teacher_allocations


class Command(BaseCommand):
    help = "Activates all users in the database and ensures they have active subscriptions."

    def handle(self, *args, **options):
        now = timezone.now()
        far_future = now + timedelta(days=3650)  # 10 years

        # 1. Ensure all users are unsuspended
        updated_users = User.objects.filter(is_suspended=True).update(is_suspended=False, is_active=True)
        self.stdout.write(f"Updated {updated_users} suspended users to active.")

        # 2. Activate all teachers
        teachers = User.objects.filter(role=User.ROLE_TEACHER)
        for teacher in teachers:
            sub, created = Subscription.objects.get_or_create(
                owner=teacher,
                defaults={
                    'subscription_type': Subscription.TYPE_TEACHER_WITH_STUDENTS,
                    'status': Subscription.STATUS_ACTIVE,
                    'paid_students_count': 500,
                    'start_date': now,
                    'end_date': far_future,
                    'notes': 'اشتراك نشط تلقائياً'
                }
            )
            if not created:
                sub.status = Subscription.STATUS_ACTIVE
                sub.paid_students_count = max(sub.paid_students_count, 500)
                sub.end_date = far_future
                sub.save()

        # 3. Activate all students
        students = User.objects.filter(role=User.ROLE_STUDENT)
        for student in students:
            membership = HalaqaMember.objects.filter(user=student, role=HalaqaMember.ROLE_STUDENT).first()
            teacher = membership.halaqa.owner if membership else None
            profile, _ = StudentSubscriptionProfile.objects.get_or_create(student=student)

            if teacher:
                profile.teacher = teacher
                profile.is_independent = False
                profile.is_covered_by_allocation = True
                profile.status_override = StudentSubscriptionProfile.OVERRIDE_AUTO
            else:
                profile.is_independent = True
                profile.is_covered_by_allocation = True
                profile.status_override = StudentSubscriptionProfile.OVERRIDE_AUTO
                sub, _ = Subscription.objects.get_or_create(
                    owner=student,
                    defaults={
                        'subscription_type': Subscription.TYPE_INDEPENDENT_STUDENT,
                        'status': Subscription.STATUS_ACTIVE,
                        'start_date': now,
                        'end_date': far_future,
                        'notes': 'اشتراك طالب مستقل نشط تلقائياً'
                    }
                )
                sub.status = Subscription.STATUS_ACTIVE
                sub.end_date = far_future
                sub.save()
            profile.save()

        # 4. Recalculate allocations
        for teacher in teachers:
            recalculate_teacher_allocations(teacher)

        self.stdout.write(self.style.SUCCESS(f"Successfully activated all {User.objects.count()} users."))


from django.core.management.base import BaseCommand
from django.utils import timezone
from subscriptions.models import Subscription, SubscriptionAuditLog
from subscriptions.services import recalculate_teacher_allocations


class Command(BaseCommand):
    help = "Checks all active subscriptions and updates expired ones based on end_date."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_subs = Subscription.objects.filter(
            status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_FREE_TRIAL],
            end_date__lt=now
        )

        count = 0
        for sub in expired_subs:
            old_status = sub.status
            sub.status = Subscription.STATUS_EXPIRED
            sub.save(update_fields=['status', 'updated_at'])

            if sub.subscription_type in [Subscription.TYPE_TEACHER_WITH_STUDENTS, Subscription.TYPE_INDIVIDUAL_TEACHER]:
                recalculate_teacher_allocations(sub.owner)

            SubscriptionAuditLog.objects.create(
                subscription=sub,
                target_user=sub.owner,
                action="EXPIRE_SUBSCRIPTION",
                details=f"تم تحديث حالة الاشتراك من ({old_status}) إلى منتهي (EXPIRED) لتجاوزه تاريخ {sub.end_date.strftime('%Y-%m-%d')}."
            )
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Finished checking subscriptions. Updated {count} expired subscriptions.")
        )


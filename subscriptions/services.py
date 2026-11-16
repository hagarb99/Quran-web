from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember
from .models import Subscription, StudentSubscriptionProfile, Payment, SubscriptionAuditLog


def get_user_subscription_status(user):
    """
    Evaluates and returns the active subscription status for a user.
    Statuses: ACTIVE, FREE_TRIAL, PENDING, PAUSED, CLOSED, EXPIRED.
    Platform admins always return ACTIVE.
    """
    if not user or not user.is_authenticated:
        return Subscription.STATUS_PENDING

    if user.is_platform_admin:
        return Subscription.STATUS_ACTIVE

    if user.role == User.ROLE_TEACHER:
        sub = Subscription.objects.filter(owner=user).order_by('-created_at').first()
        if not sub:
            return Subscription.STATUS_PENDING
        return sub.dynamic_status

    if user.role == User.ROLE_STUDENT:
        profile, _ = StudentSubscriptionProfile.objects.get_or_create(student=user)

        # Check explicit individual administrative override
        if profile.status_override != StudentSubscriptionProfile.OVERRIDE_AUTO:
            return profile.status_override

        # Independent student with their own subscription
        if profile.is_independent or (profile.teacher is None and Subscription.objects.filter(owner=user, subscription_type=Subscription.TYPE_INDEPENDENT_STUDENT).exists()):
            sub = Subscription.objects.filter(
                owner=user,
                subscription_type=Subscription.TYPE_INDEPENDENT_STUDENT
            ).order_by('-created_at').first()
            if not sub:
                return Subscription.STATUS_PENDING
            return sub.dynamic_status

        # Student belonging to a Teacher
        teacher = profile.teacher
        if not teacher:
            return Subscription.STATUS_PENDING

        teacher_sub = Subscription.objects.filter(owner=teacher).order_by('-created_at').first()
        if not teacher_sub:
            return Subscription.STATUS_PENDING

        teacher_status = teacher_sub.dynamic_status
        if teacher_status not in [Subscription.STATUS_ACTIVE, Subscription.STATUS_FREE_TRIAL]:
            # Student inherits teacher's restriction
            return teacher_status

        # Teacher has active subscription -> verify student is covered by paid allocation
        if profile.is_covered_by_allocation:
            return Subscription.STATUS_ACTIVE
        else:
            return Subscription.STATUS_PENDING

    return Subscription.STATUS_PENDING


def has_active_access(user):
    """
    Returns True if user has full active/free-trial access.
    """
    status = get_user_subscription_status(user)
    return status in [Subscription.STATUS_ACTIVE, Subscription.STATUS_FREE_TRIAL]


def get_teacher_unique_students(teacher):
    """
    Returns QuerySet of unique student Users currently belonging to this teacher
    for subscription tracking (excluding students who transferred to independent or another teacher).
    """
    # 1. Students explicitly profiled under this teacher (and not independent)
    profile_student_ids = set(StudentSubscriptionProfile.objects.filter(
        teacher=teacher,
        is_independent=False
    ).values_list('student_id', flat=True))

    # 2. Students in teacher's halaqat who do NOT have a profile assigning them elsewhere or independent
    halaqat_student_ids = set(HalaqaMember.objects.filter(
        halaqa__owner=teacher,
        role=HalaqaMember.ROLE_STUDENT
    ).values_list('user_id', flat=True))

    # Exclude students who are independent or belong to another teacher
    excluded_ids = set(StudentSubscriptionProfile.objects.filter(
        Q(is_independent=True) | (~Q(teacher=teacher) & Q(teacher__isnull=False))
    ).values_list('student_id', flat=True))

    active_halaqat_ids = halaqat_student_ids - excluded_ids
    all_student_ids = profile_student_ids.union(active_halaqat_ids)

    return User.objects.filter(id__in=all_student_ids, role=User.ROLE_STUDENT)


def recalculate_teacher_allocations(teacher, actor=None):
    """
    Recalculates which students are covered by the Teacher's paid subscription allocation.
    Order of assignment (FIFO) determines which unique students get the paid slots.
    Existing students retain priority; newly added students beyond allocation become PENDING.
    """
    sub = Subscription.objects.filter(owner=teacher).order_by('-created_at').first()
    paid_slots = sub.paid_students_count if sub and sub.is_currently_active else 0

    # Ensure profiles exist for all students enrolled in this teacher's halaqat
    unique_students = get_teacher_unique_students(teacher)
    for st in unique_students:
        profile, created = StudentSubscriptionProfile.objects.get_or_create(student=st)
        if not profile.teacher and not profile.is_independent:
            profile.teacher = teacher
            profile.save(update_fields=['teacher'])

    # Fetch all profiles assigned to this teacher ordered by assignment date
    profiles = list(StudentSubscriptionProfile.objects.filter(
        teacher=teacher
    ).order_by('assigned_at', 'id'))

    for index, profile in enumerate(profiles):
        should_be_covered = (index < paid_slots)
        if profile.is_covered_by_allocation != should_be_covered:
            profile.is_covered_by_allocation = should_be_covered
            profile.save(update_fields=['is_covered_by_allocation'])


def assign_student_to_teacher(student, teacher, actor=None):
    """
    Safely assigns a student to a teacher.
    Validates that student does not belong to another teacher.
    """
    profile, _ = StudentSubscriptionProfile.objects.get_or_create(student=student)
    if profile.teacher and profile.teacher != teacher:
        raise ValidationError(
            f"لا يمكن إضافة الطالب {student.display_name}: الطالب مسجل بالفعل تحت اشتراك المعلم '{profile.teacher.display_name}'. يجب نقله أولاً."
        )

    profile.teacher = teacher
    profile.is_independent = False
    profile.save(update_fields=['teacher', 'is_independent'])

    recalculate_teacher_allocations(teacher, actor=actor)

    SubscriptionAuditLog.objects.create(
        actor=actor,
        target_user=student,
        action="ASSIGN_TO_TEACHER",
        details=f"تم إسناد الطالب {student.display_name} لاشتراك المعلم {teacher.display_name}."
    )


def transfer_student_to_independent(student, actor=None, notes=""):
    """
    Safely transfers a student from their teacher to Independent Student status.
    Preserves all historical data, attendance, recitations, and previous Halaqa records.
    Removes the student from the Teacher's current student count.
    """
    with transaction.atomic():
        profile, _ = StudentSubscriptionProfile.objects.get_or_create(student=student)
        old_teacher = profile.teacher

        profile.teacher = None
        profile.is_independent = True
        profile.is_covered_by_allocation = False
        profile.status_override = StudentSubscriptionProfile.OVERRIDE_AUTO
        profile.transferred_at = timezone.now()
        profile.save()

        if old_teacher:
            recalculate_teacher_allocations(old_teacher, actor=actor)

        # Create or update independent subscription record for the student
        now = timezone.now()
        sub, _ = Subscription.objects.get_or_create(
            owner=student,
            defaults={
                'subscription_type': Subscription.TYPE_INDEPENDENT_STUDENT,
                'status': Subscription.STATUS_PENDING,
                'start_date': now,
                'end_date': now + timedelta(days=30),
                'notes': f"تم إنشاء اشتراك مستقل بعد النقل من المعلم. {notes}".strip(),
            }
        )

        SubscriptionAuditLog.objects.create(
            actor=actor,
            target_user=student,
            action="TRANSFER_TO_INDEPENDENT",
            details=f"تم تحويل الطالب {student.display_name} من المعلم ({old_teacher.display_name if old_teacher else 'لا يوجد'}) إلى طالب مستقل. {notes}"
        )


def activate_subscription(subscription, actor=None, notes=""):
    """
    Activates or approves a subscription.
    """
    with transaction.atomic():
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.save(update_fields=['status', 'updated_at'])

        if subscription.subscription_type in [Subscription.TYPE_TEACHER_WITH_STUDENTS, Subscription.TYPE_INDIVIDUAL_TEACHER]:
            recalculate_teacher_allocations(subscription.owner, actor=actor)

        date_str = subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else 'غير محدد'
        SubscriptionAuditLog.objects.create(
            subscription=subscription,
            actor=actor,
            target_user=subscription.owner,
            action="ACTIVATE_SUBSCRIPTION",
            details=f"تم تفعيل الاشتراك ({subscription.get_subscription_type_display()}) حتى {date_str}. {notes}"
        )


def renew_subscription(subscription, new_end_date, new_paid_students_count=None, amount=None, payment_ref="", verified_by=None, actor=None, notes=""):
    """
    Renews a subscription for a new period, optionally recording a manual payment.
    Preserves all historical records.
    """
    with transaction.atomic():
        subscription.end_date = new_end_date
        subscription.status = Subscription.STATUS_ACTIVE
        if new_paid_students_count is not None:
            subscription.paid_students_count = new_paid_students_count
        subscription.save(update_fields=['end_date', 'status', 'paid_students_count', 'updated_at'])

        if amount:
            Payment.objects.create(
                subscription=subscription,
                amount=amount,
                currency='EGP',
                payment_method=Payment.METHOD_INSTAPAY,
                transaction_reference=payment_ref,
                verified_by=verified_by or actor,
                notes=notes
            )

        if subscription.subscription_type in [Subscription.TYPE_TEACHER_WITH_STUDENTS, Subscription.TYPE_INDIVIDUAL_TEACHER]:
            recalculate_teacher_allocations(subscription.owner, actor=actor)

        SubscriptionAuditLog.objects.create(
            subscription=subscription,
            actor=actor,
            target_user=subscription.owner,
            action="RENEW_SUBSCRIPTION",
            details=f"تم تجديد الاشتراك حتى {new_end_date.strftime('%Y-%m-%d')} بمقاعد: {subscription.paid_students_count}. {notes}"
        )


def pause_subscription(subscription, actor=None, notes=""):
    """
    Pauses an active subscription.
    """
    with transaction.atomic():
        subscription.status = Subscription.STATUS_PAUSED
        subscription.save(update_fields=['status', 'updated_at'])

        if subscription.subscription_type in [Subscription.TYPE_TEACHER_WITH_STUDENTS, Subscription.TYPE_INDIVIDUAL_TEACHER]:
            recalculate_teacher_allocations(subscription.owner, actor=actor)

        SubscriptionAuditLog.objects.create(
            subscription=subscription,
            actor=actor,
            target_user=subscription.owner,
            action="PAUSE_SUBSCRIPTION",
            details=f"تم إيقاف الاشتراك مؤقتاً. {notes}"
        )


def close_subscription(subscription, actor=None, notes=""):
    """
    Permanently closes a subscription while preserving all data.
    """
    with transaction.atomic():
        subscription.status = Subscription.STATUS_CLOSED
        subscription.save(update_fields=['status', 'updated_at'])

        if subscription.subscription_type in [Subscription.TYPE_TEACHER_WITH_STUDENTS, Subscription.TYPE_INDIVIDUAL_TEACHER]:
            recalculate_teacher_allocations(subscription.owner, actor=actor)

        SubscriptionAuditLog.objects.create(
            subscription=subscription,
            actor=actor,
            target_user=subscription.owner,
            action="CLOSE_SUBSCRIPTION",
            details=f"تم إغلاق الاشتراك نهائياً. {notes}"
        )

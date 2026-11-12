from django.db import models
from django.conf import settings
from django.utils import timezone
from halaqa_sessions.models import Session


class RecitationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        return super().get_queryset()


class Recitation(models.Model):
    # Rating options: strictly performance levels only, NO star ratings
    RATING_MUMTAZ = 'MUMTAZ'
    RATING_JAYYID_JIDDAN = 'JAYYID_JIDDAN'
    RATING_JAYYID = 'JAYYID'
    RATING_MAQBOOL = 'MAQBOOL'
    RATING_DAEEF = 'DAEEF'

    RATING_CHOICES = [
        (RATING_MUMTAZ, 'ممتاز'),
        (RATING_JAYYID_JIDDAN, 'جيد جدًا'),
        (RATING_JAYYID, 'جيد'),
        (RATING_MAQBOOL, 'مقبول'),
        (RATING_DAEEF, 'ضعيف'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='recitations', verbose_name="الجلسة")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recitation_records', verbose_name="الطالب")
    
    new_memorization = models.CharField(max_length=255, blank=True, verbose_name="الحفظ الجديد")
    near_revision = models.CharField(max_length=255, blank=True, verbose_name="المراجعة القريبة")
    far_revision = models.CharField(max_length=255, blank=True, verbose_name="المراجعة البعيدة")
    rating = models.CharField(max_length=20, choices=RATING_CHOICES, verbose_name="مستوى الأداء")
    teacher_notes = models.TextField(blank=True, verbose_name="ملاحظات المعلم")
    next_assignment = models.TextField(blank=True, verbose_name="الواجب القادم")

    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسجيل")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_recitations',
        verbose_name="سُجل بواسطة"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_recitations',
        verbose_name="عُدل بواسطة"
    )

    # Soft deletion
    is_deleted = models.BooleanField(default=False, verbose_name="محذوف")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحذف")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_recitations',
        verbose_name="حُذف بواسطة"
    )

    objects = RecitationManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "سجل تسميع"
        verbose_name_plural = "سجلات التسميع"
        ordering = ['-session__date', 'student__first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                condition=models.Q(is_deleted=False),
                name='unique_active_session_student_recitation'
            )
        ]

    def __str__(self):
        return f"تسميع {self.student.display_name} - {self.get_rating_display()} ({self.session.title})"

    def soft_delete(self, user):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

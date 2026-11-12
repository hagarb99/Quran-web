from django.db import models
from django.conf import settings
from django.utils import timezone
from halaqa_sessions.models import Session


class AttendanceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        return super().get_queryset()


class Attendance(models.Model):
    STATUS_PRESENT = 'PRESENT'
    STATUS_ABSENT = 'ABSENT'
    STATUS_LATE = 'LATE'
    STATUS_EXCUSED = 'EXCUSED'

    STATUS_CHOICES = [
        (STATUS_PRESENT, 'حاضر'),
        (STATUS_ABSENT, 'غائب'),
        (STATUS_LATE, 'متأخر'),
        (STATUS_EXCUSED, 'معذور'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendances', verbose_name="الجلسة")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records', verbose_name="الطالب")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PRESENT, verbose_name="حالة الحضور")
    notes = models.TextField(blank=True, verbose_name="ملاحظات الحضور")

    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسجيل")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_attendances',
        verbose_name="سُجل بواسطة"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_attendances',
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
        related_name='deleted_attendances',
        verbose_name="حُذف بواسطة"
    )

    objects = AttendanceManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "سجل حضور"
        verbose_name_plural = "سجلات الحضور"
        ordering = ['-session__date', 'student__first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                condition=models.Q(is_deleted=False),
                name='unique_active_session_student_attendance'
            )
        ]

    def __str__(self):
        return f"{self.student.display_name} - {self.get_status_display()} ({self.session.title})"

    def soft_delete(self, user):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

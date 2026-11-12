from django.db import models
from django.conf import settings
from django.utils import timezone
from halaqat.models import Halaqa


class SessionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        return super().get_queryset()


class Session(models.Model):
    STATUS_SCHEDULED = 'SCHEDULED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'مجدولة'),
        (STATUS_IN_PROGRESS, 'جارية الآن'),
        (STATUS_COMPLETED, 'مكتملة'),
        (STATUS_CANCELLED, 'ملغاة'),
    ]

    halaqa = models.ForeignKey(Halaqa, on_delete=models.CASCADE, related_name='sessions', verbose_name="الحلقة")
    title = models.CharField(max_length=200, verbose_name="عنوان الجلسة")
    date = models.DateField(verbose_name="تاريخ الجلسة")
    start_time = models.TimeField(verbose_name="وقت البدء")
    end_time = models.TimeField(null=True, blank=True, verbose_name="وقت الانتهاء")
    meet_url = models.URLField(blank=True, verbose_name="رابط Google Meet")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, verbose_name="حالة الجلسة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات الجلسة")

    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sessions',
        verbose_name="أُنشئت بواسطة"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_sessions',
        verbose_name="عُدلت بواسطة"
    )

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإكمال")
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_sessions',
        verbose_name="أُكملت بواسطة"
    )

    reopened_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ إعادة الفتح")
    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reopened_sessions',
        verbose_name="أُعيد فتحها بواسطة"
    )

    # Soft deletion
    is_deleted = models.BooleanField(default=False, verbose_name="محذوفة")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحذف")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_sessions',
        verbose_name="حُذفت بواسطة"
    )

    objects = SessionManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "جلسة"
        verbose_name_plural = "الجلسات"
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.title} - {self.halaqa.name} ({self.date.strftime('%Y-%m-%d')} {self.start_time.strftime('%H:%M')})"

    def mark_completed(self, user):
        """Rule 5: Cancelled sessions cannot be completed."""
        if self.status == self.STATUS_CANCELLED:
            raise ValueError("لا يمكن إكمال جلسة ملغاة.")
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save()

    def reopen(self, user):
        """Rule 6 & 7: Completed sessions can be reopened; they become IN_PROGRESS."""
        if self.status != self.STATUS_COMPLETED:
            raise ValueError("فقط الجلسات المكتملة يمكن إعادة فتحها.")
        self.status = self.STATUS_IN_PROGRESS
        self.reopened_at = timezone.now()
        self.reopened_by = user
        self.save()

    def cancel(self, user):
        self.status = self.STATUS_CANCELLED
        self.updated_by = user
        self.save()

    def soft_delete(self, user):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Halaqa(models.Model):
    GENDER_MALE = 'MALE'
    GENDER_FEMALE = 'FEMALE'
    GENDER_CHOICES = [
        (GENDER_MALE, 'رجال (ذكور)'),
        (GENDER_FEMALE, 'نساء (إناث)'),
    ]

    VISIBILITY_PUBLIC = 'PUBLIC'
    VISIBILITY_PRIVATE = 'PRIVATE'
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, 'عامة (تظهر في التصفح ويمكن طلب الانضمام)'),
        (VISIBILITY_PRIVATE, 'خاصة (مخفية، الانضمام بالدعوة فقط)'),
    ]

    name = models.CharField(max_length=150, verbose_name="اسم الحلقة")
    description = models.TextField(blank=True, verbose_name="وصف الحلقة")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="الفئة (الجنس)")
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PUBLIC, verbose_name="الظهور")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_halaqat',
        verbose_name="مالك الحلقة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "حلقة قرآنية"
        verbose_name_plural = "الحلقات القرآنية"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

    def get_member(self, user):
        if not user or not user.is_authenticated:
            return None
        return self.members.filter(user=user).first()

    def is_owner(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.owner_id == user.id

    def can_manage_halaqa(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_platform_admin or self.is_owner(user):
            return True
        member = self.get_member(user)
        if not member:
            return False
        if member.role == HalaqaMember.ROLE_TEACHER:
            return True
        if member.role == HalaqaMember.ROLE_ASSISTANT and member.can_manage_members:
            return True
        return False

    def can_manage_sessions(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_platform_admin or self.is_owner(user):
            return True
        member = self.get_member(user)
        if not member:
            return False
        if member.role == HalaqaMember.ROLE_TEACHER:
            return True
        if member.role == HalaqaMember.ROLE_ASSISTANT and member.can_manage_sessions:
            return True
        return False

    def can_record_attendance(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_platform_admin or self.is_owner(user):
            return True
        member = self.get_member(user)
        if not member:
            return False
        if member.role == HalaqaMember.ROLE_TEACHER:
            return True
        if member.role == HalaqaMember.ROLE_ASSISTANT and member.can_record_attendance:
            return True
        return False

    def can_record_recitation(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_platform_admin or self.is_owner(user):
            return True
        member = self.get_member(user)
        if not member:
            return False
        if member.role == HalaqaMember.ROLE_TEACHER:
            return True
        if member.role == HalaqaMember.ROLE_ASSISTANT and member.can_record_recitation:
            return True
        return False


class HalaqaMember(models.Model):
    ROLE_OWNER = 'OWNER'
    ROLE_TEACHER = 'TEACHER'
    ROLE_ASSISTANT = 'ASSISTANT'
    ROLE_STUDENT = 'STUDENT'
    
    ROLE_CHOICES = [
        (ROLE_OWNER, 'مالك الحلقة'),
        (ROLE_TEACHER, 'معلم'),
        (ROLE_ASSISTANT, 'مساعد'),
        (ROLE_STUDENT, 'طالب'),
    ]

    halaqa = models.ForeignKey(Halaqa, on_delete=models.CASCADE, related_name='members', verbose_name="الحلقة")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='halaqa_memberships', verbose_name="المستخدم")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT, verbose_name="دور العضوية")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانضمام")

    # Assistant granular permissions (per Halaqa)
    can_manage_sessions = models.BooleanField(default=True, verbose_name="إدارة الجلسات")
    can_record_attendance = models.BooleanField(default=True, verbose_name="تسجيل الحضور")
    can_record_recitation = models.BooleanField(default=True, verbose_name="تسجيل التسميع")
    can_manage_members = models.BooleanField(default=False, verbose_name="إدارة الأعضاء")

    class Meta:
        verbose_name = "عضو الحلقة"
        verbose_name_plural = "أعضاء الحلقات"
        unique_together = ('halaqa', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.display_name} - {self.get_role_display()} في {self.halaqa.name}"

    def clean(self):
        # Business rule 8: Students can only join Halaqat matching their gender
        # Business rule 9: Teachers and assistants can manage both male and female Halaqat
        if self.role == self.ROLE_STUDENT:
            if self.user.gender != self.halaqa.gender:
                raise ValidationError("لا يمكن للطالب الانضمام لحلقة لا تطابق جنسه.")


class HalaqaSchedule(models.Model):
    DAY_CHOICES = [
        (0, 'السبت'),
        (1, 'الأحد'),
        (2, 'الإثنين'),
        (3, 'الثلاثاء'),
        (4, 'الأربعاء'),
        (5, 'الخميس'),
        (6, 'الجمعة'),
    ]

    halaqa = models.ForeignKey(Halaqa, on_delete=models.CASCADE, related_name='schedules', verbose_name="الحلقة")
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name="اليوم")
    start_time = models.TimeField(verbose_name="وقت البدء")
    end_time = models.TimeField(verbose_name="وقت الانتهاء")
    notes = models.CharField(max_length=200, blank=True, verbose_name="ملاحظات الموعد")

    class Meta:
        verbose_name = "موعد الحلقة"
        verbose_name_plural = "مواعيد الحلقات"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.halaqa.name} - {self.get_day_of_week_display()} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class JoinRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'قيد الانتظار'),
        (STATUS_APPROVED, 'تمت الموافقة'),
        (STATUS_REJECTED, 'مرفوض'),
    ]

    halaqa = models.ForeignKey(Halaqa, on_delete=models.CASCADE, related_name='join_requests', verbose_name="الحلقة")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='join_requests', verbose_name="الطالب")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="حالة الطلب")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ المراجعة")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests',
        verbose_name="تمت المراجعة بواسطة"
    )

    class Meta:
        verbose_name = "طلب انضمام"
        verbose_name_plural = "طلبات الانضمام"
        ordering = ['-created_at']

    def __str__(self):
        return f"طلب {self.user.display_name} للحلقة {self.halaqa.name} ({self.get_status_display()})"

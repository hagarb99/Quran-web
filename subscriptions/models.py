from django.db import models
from django.conf import settings
from django.utils import timezone


class Subscription(models.Model):
    TYPE_TEACHER_WITH_STUDENTS = 'TEACHER_WITH_STUDENTS'
    TYPE_INDIVIDUAL_TEACHER = 'INDIVIDUAL_TEACHER'
    TYPE_INDEPENDENT_STUDENT = 'INDEPENDENT_STUDENT'

    TYPE_CHOICES = [
        (TYPE_TEACHER_WITH_STUDENTS, 'معلم مع طلابه'),
        (TYPE_INDIVIDUAL_TEACHER, 'معلم فردي'),
        (TYPE_INDEPENDENT_STUDENT, 'طالب مستقل'),
    ]

    STATUS_FREE_TRIAL = 'FREE_TRIAL'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_PENDING = 'PENDING'
    STATUS_PAUSED = 'PAUSED'
    STATUS_CLOSED = 'CLOSED'
    STATUS_EXPIRED = 'EXPIRED'

    STATUS_CHOICES = [
        (STATUS_FREE_TRIAL, 'فترة تجريبية مجانية'),
        (STATUS_ACTIVE, 'نشط'),
        (STATUS_PENDING, 'قيد الانتظار'),
        (STATUS_PAUSED, 'موقوف مؤقتاً'),
        (STATUS_CLOSED, 'مغلق'),
        (STATUS_EXPIRED, 'منتهي الصلاحية'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name="صاحب الاشتراك"
    )
    subscription_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_TEACHER_WITH_STUDENTS,
        verbose_name="نوع الاشتراك",
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="حالة الاشتراك",
        db_index=True
    )
    paid_students_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الطلاب المدفوع (المقاعد)"
    )
    start_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="تاريخ البدء"
    )
    end_date = models.DateTimeField(
        verbose_name="تاريخ الانتهاء",
        db_index=True
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات الاشتراك"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث"
    )

    class Meta:
        verbose_name = "اشتراك منصة"
        verbose_name_plural = "الاشتراكات"
        ordering = ['-created_at']

    def __str__(self):
        return f"اشتراك {self.owner.display_name} ({self.get_subscription_type_display()} - {self.get_status_display()})"

    @property
    def dynamic_status(self):
        """
        Dynamically returns EXPIRED if current time is past end_date,
        ensuring access restrictions apply immediately without waiting for cron/management command.
        """
        if self.status in [self.STATUS_ACTIVE, self.STATUS_FREE_TRIAL]:
            if self.end_date and timezone.now() > self.end_date:
                return self.STATUS_EXPIRED
        return self.status

    @property
    def is_currently_active(self):
        return self.dynamic_status in [self.STATUS_ACTIVE, self.STATUS_FREE_TRIAL]


class StudentSubscriptionProfile(models.Model):
    OVERRIDE_AUTO = 'AUTO'
    OVERRIDE_ACTIVE = 'ACTIVE'
    OVERRIDE_PAUSED = 'PAUSED'
    OVERRIDE_CLOSED = 'CLOSED'
    OVERRIDE_PENDING = 'PENDING'

    OVERRIDE_CHOICES = [
        (OVERRIDE_AUTO, 'تلقائي (حسب اشتراك المعلم وتخصيص المقاعد)'),
        (OVERRIDE_ACTIVE, 'نشط (تجاوز إداري صريح)'),
        (OVERRIDE_PAUSED, 'موقوف مؤقتاً (إدارياً)'),
        (OVERRIDE_CLOSED, 'مغلق نهائياً (إدارياً)'),
        (OVERRIDE_PENDING, 'قيد الانتظار (إدارياً)'),
    ]

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_profile',
        verbose_name="الطالب"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_student_profiles',
        verbose_name="المعلم التابع له (مالك الاشتراك)"
    )
    is_independent = models.BooleanField(
        default=False,
        verbose_name="طالب مستقل (غير تابع لمعلم)"
    )
    status_override = models.CharField(
        max_length=20,
        choices=OVERRIDE_CHOICES,
        default=OVERRIDE_AUTO,
        verbose_name="التحكم الإداري الفردي بالحالة"
    )
    is_covered_by_allocation = models.BooleanField(
        default=False,
        verbose_name="مغطى بالمقاعد المدفوعة للمعلم"
    )
    assigned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="تاريخ الإسناد للمعلم"
    )
    transferred_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ التحويل إلى مستقل"
    )

    class Meta:
        verbose_name = "ملف اشتراك الطالب وتبعيته"
        verbose_name_plural = "ملفات اشتراكات الطلاب"

    def __str__(self):
        owner_name = "مستقل" if self.is_independent else (self.teacher.display_name if self.teacher else "غير مسند")
        return f"ملف الطالب: {self.student.display_name} -> {owner_name}"


class Payment(models.Model):
    METHOD_INSTAPAY = 'InstaPay'
    METHOD_CASH = 'CASH'
    METHOD_BANK_TRANSFER = 'BANK_TRANSFER'
    METHOD_OTHER = 'OTHER'

    METHOD_CHOICES = [
        (METHOD_INSTAPAY, 'إنستاباي (InstaPay)'),
        (METHOD_CASH, 'نقدي'),
        (METHOD_BANK_TRANSFER, 'تحويل بنكي'),
        (METHOD_OTHER, 'أخرى'),
    ]

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="الاشتراك المرتبط"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="المبلغ المدفوع"
    )
    currency = models.CharField(
        max_length=10,
        default='EGP',
        verbose_name="العملة"
    )
    payment_method = models.CharField(
        max_length=30,
        choices=METHOD_CHOICES,
        default=METHOD_INSTAPAY,
        verbose_name="طريقة الدفع"
    )
    payment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="تاريخ الدفع"
    )
    transaction_reference = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="الرقم المرجعي للعملية (إنستاباي)"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        verbose_name="تم التحقق بواسطة المشرف"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات العملية"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ التسجيل"
    )

    class Meta:
        verbose_name = "سجل دفعة مالية"
        verbose_name_plural = "سجل المدفوعات المالية"
        ordering = ['-payment_date']

    def __str__(self):
        return f"دفعة {self.amount} {self.currency} - {self.subscription.owner.display_name} ({self.get_payment_method_display()})"


class SubscriptionAuditLog(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="الاشتراك"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_subscription_actions',
        verbose_name="منفذ الإجراء (المشرف)"
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_audit_records',
        verbose_name="المستخدم المعني"
    )
    action = models.CharField(
        max_length=50,
        verbose_name="نوع الإجراء"
    )
    details = models.TextField(
        blank=True,
        verbose_name="تفاصيل الإجراء"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإجراء"
    )

    class Meta:
        verbose_name = "سجل تدقيق الاشتراكات"
        verbose_name_plural = "سجلات تدقيق الاشتراكات"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.action} على {self.target_user.display_name}"

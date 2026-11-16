from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from accounts.models import User
from .models import Subscription, StudentSubscriptionProfile, Payment, SubscriptionAuditLog
from .services import (
    activate_subscription,
    pause_subscription,
    close_subscription,
    renew_subscription,
    transfer_student_to_independent,
    recalculate_teacher_allocations,
    get_teacher_unique_students,
    get_user_subscription_status
)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('amount', 'currency', 'payment_method', 'transaction_reference', 'payment_date', 'verified_by', 'notes')
    readonly_fields = ('created_at',)


class StudentProfileInline(admin.TabularInline):
    model = StudentSubscriptionProfile
    extra = 0
    fk_name = 'teacher'
    fields = ('student', 'is_covered_by_allocation', 'status_override', 'assigned_at')
    readonly_fields = ('student', 'assigned_at')
    can_delete = False
    verbose_name = "طالب مسند لهذا المعلم"
    verbose_name_plural = "الطلاب التابعون لاشتراك المعلم"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'owner_name',
        'subscription_type_badge',
        'status_badge',
        'paid_students_count',
        'covered_students_count',
        'start_date',
        'end_date',
        'expiration_indicator'
    )
    list_filter = ('subscription_type', 'status', 'start_date', 'end_date')
    search_fields = (
        'owner__username',
        'owner__first_name',
        'owner__last_name',
        'owner__phone',
        'owner__email'
    )
    date_hierarchy = 'end_date'
    inlines = [PaymentInline]
    actions = [
        'action_activate',
        'action_pause',
        'action_close',
        'action_renew_one_month',
        'action_recalculate_students'
    ]

    def owner_name(self, obj):
        return f"{obj.owner.display_name} ({obj.owner.phone})"
    owner_name.short_description = "صاحب الاشتراك"

    def subscription_type_badge(self, obj):
        colors = {
            Subscription.TYPE_TEACHER_WITH_STUDENTS: '#064E3B',
            Subscription.TYPE_INDIVIDUAL_TEACHER: '#0284C7',
            Subscription.TYPE_INDEPENDENT_STUDENT: '#D97706',
        }
        color = colors.get(obj.subscription_type, '#334155')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_subscription_type_display()
        )
    subscription_type_badge.short_description = "نوع الاشتراك"

    def status_badge(self, obj):
        dyn = obj.dynamic_status
        colors = {
            Subscription.STATUS_ACTIVE: '#10B981',
            Subscription.STATUS_FREE_TRIAL: '#0284C7',
            Subscription.STATUS_PENDING: '#F59E0B',
            Subscription.STATUS_PAUSED: '#EAB308',
            Subscription.STATUS_CLOSED: '#64748B',
            Subscription.STATUS_EXPIRED: '#EF4444',
        }
        labels = dict(Subscription.STATUS_CHOICES)
        color = colors.get(dyn, '#64748B')
        label = labels.get(dyn, dyn)
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            label
        )
    status_badge.short_description = "الحالة الفعلية"

    def covered_students_count(self, obj):
        if obj.subscription_type == Subscription.TYPE_TEACHER_WITH_STUDENTS:
            covered = StudentSubscriptionProfile.objects.filter(
                teacher=obj.owner,
                is_covered_by_allocation=True
            ).count()
            total = StudentSubscriptionProfile.objects.filter(teacher=obj.owner).count()
            return f"{covered} مغطى من أصل {total}"
        return "-"
    covered_students_count.short_description = "تغطية المقاعد"

    def expiration_indicator(self, obj):
        if not obj.end_date:
            return "غير محدد"
        now = timezone.now()
        if now > obj.end_date:
            days_ago = (now - obj.end_date).days
            return format_html('<span style="color: #EF4444; font-weight: bold;">منتهي منذ {} يوم</span>', days_ago)
        days_left = (obj.end_date - now).days
        return format_html('<span style="color: #10B981; font-weight: bold;">متبقي {} يوم</span>', days_left)
    expiration_indicator.short_description = "الصلاحية"

    # Admin actions
    @admin.action(description="تفعيل الاشتراكات المحددة وتغطية مقاعد الطلاب")
    def action_activate(self, request, queryset):
        count = 0
        for sub in queryset:
            activate_subscription(sub, actor=request.user)
            count += 1
        self.message_user(request, f"تم تفعيل {count} اشتراك بنجاح.")

    @admin.action(description="إيقاف الاشتراكات المحددة مؤقتاً (PAUSE)")
    def action_pause(self, request, queryset):
        count = 0
        for sub in queryset:
            pause_subscription(sub, actor=request.user)
            count += 1
        self.message_user(request, f"تم إيقاف {count} اشتراك مؤقتاً.")

    @admin.action(description="إغلاق الاشتراكات المحددة نهائياً (CLOSE)")
    def action_close(self, request, queryset):
        count = 0
        for sub in queryset:
            close_subscription(sub, actor=request.user)
            count += 1
        self.message_user(request, f"تم إغلاق {count} اشتراك نهائياً مع حفظ السجلات.")

    @admin.action(description="تجديد شهر إضافي (30 يوم) للاشتراكات المحددة")
    def action_renew_one_month(self, request, queryset):
        count = 0
        now = timezone.now()
        for sub in queryset:
            base_date = sub.end_date if (sub.end_date and sub.end_date > now) else now
            new_date = base_date + timedelta(days=30)
            renew_subscription(sub, new_end_date=new_date, actor=request.user)
            count += 1
        self.message_user(request, f"تم تجديد {count} اشتراك لمدة 30 يوماً بنجاح.")

    @admin.action(description="إعادة احتساب مقاعد الطلاب وفق الحصص المدفوعة")
    def action_recalculate_students(self, request, queryset):
        count = 0
        for sub in queryset:
            if sub.subscription_type in [Subscription.TYPE_TEACHER_WITH_STUDENTS, Subscription.TYPE_INDIVIDUAL_TEACHER]:
                recalculate_teacher_allocations(sub.owner, actor=request.user)
                count += 1
        self.message_user(request, f"تمت إعادة توزيع المقاعد لـ {count} معلم بنجاح.")


@admin.register(StudentSubscriptionProfile)
class StudentSubscriptionProfileAdmin(admin.ModelAdmin):
    list_display = (
        'student_name',
        'owner_type',
        'assigned_teacher',
        'is_covered_badge',
        'effective_status_badge',
        'status_override',
        'assigned_at'
    )
    list_filter = ('is_independent', 'is_covered_by_allocation', 'status_override', 'assigned_at')
    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'student__phone',
        'teacher__username',
        'teacher__first_name'
    )
    actions = [
        'action_transfer_to_independent',
        'action_set_active_override',
        'action_set_paused_override',
        'action_set_auto_override'
    ]

    def student_name(self, obj):
        return f"{obj.student.display_name} ({obj.student.phone})"
    student_name.short_description = "الطالب"

    def owner_type(self, obj):
        if obj.is_independent:
            return format_html('<span style="color: #D97706; font-weight: bold;">طالب مستقل</span>')
        return format_html('<span style="color: #064E3B;">تابع لمعلم</span>')
    owner_type.short_description = "نوع التبعية"

    def assigned_teacher(self, obj):
        if obj.teacher:
            return f"{obj.teacher.display_name} ({obj.teacher.phone})"
        return "لا يوجد"
    assigned_teacher.short_description = "المعلم التابع له"

    def is_covered_badge(self, obj):
        if obj.is_independent:
            return "-"
        if obj.is_covered_by_allocation:
            return format_html('<span style="color: #10B981; font-weight: bold;">✔ مشمول بالمقاعد</span>')
        return format_html('<span style="color: #EF4444; font-weight: bold;">✖ غير مشمول (معلق)</span>')
    is_covered_badge.short_description = "المقعد المدفوع"

    def effective_status_badge(self, obj):
        st = get_user_subscription_status(obj.student)
        colors = {
            'ACTIVE': '#10B981',
            'FREE_TRIAL': '#0284C7',
            'PENDING': '#F59E0B',
            'PAUSED': '#EAB308',
            'CLOSED': '#64748B',
            'EXPIRED': '#EF4444',
        }
        color = colors.get(st, '#64748B')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 2px 7px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            st
        )
    effective_status_badge.short_description = "الحالة النهائية للوصول"

    # Actions
    @admin.action(description="تحويل الطلاب المحددين إلى (طلاب مستقلين)")
    def action_transfer_to_independent(self, request, queryset):
        count = 0
        for profile in queryset:
            transfer_student_to_independent(profile.student, actor=request.user)
            count += 1
        self.message_user(request, f"تم تحويل {count} طالب إلى صفة طالب مستقل مع حفظ كامل سجلاتهم.")

    @admin.action(description="تجاوز إداري: تفعيل وصول الطالب يدوياً (ACTIVE)")
    def action_set_active_override(self, request, queryset):
        queryset.update(status_override=StudentSubscriptionProfile.OVERRIDE_ACTIVE)
        self.message_user(request, "تم تفعيل وصول الطلاب المحددين إدارياً.")

    @admin.action(description="تجاوز إداري: إيقاف وصول الطالب يدوياً (PAUSED)")
    def action_set_paused_override(self, request, queryset):
        queryset.update(status_override=StudentSubscriptionProfile.OVERRIDE_PAUSED)
        self.message_user(request, "تم إيقاف وصول الطلاب المحددين إدارياً.")

    @admin.action(description="إلغاء التجاوز الإداري وإعادة الحالة إلى تلقائي (AUTO)")
    def action_set_auto_override(self, request, queryset):
        queryset.update(status_override=StudentSubscriptionProfile.OVERRIDE_AUTO)
        self.message_user(request, "تمت إعادة حالة الطلاب إلى الوضع التلقائي.")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'subscription_owner',
        'amount_display',
        'payment_method_badge',
        'transaction_reference',
        'payment_date',
        'verified_by',
        'created_at'
    )
    list_filter = ('payment_method', 'currency', 'payment_date')
    search_fields = (
        'subscription__owner__username',
        'subscription__owner__phone',
        'transaction_reference',
        'notes'
    )
    date_hierarchy = 'payment_date'

    def subscription_owner(self, obj):
        return f"{obj.subscription.owner.display_name} ({obj.subscription.owner.phone})"
    subscription_owner.short_description = "صاحب الاشتراك"

    def amount_display(self, obj):
        return f"{obj.amount} {obj.currency}"
    amount_display.short_description = "المبلغ"

    def payment_method_badge(self, obj):
        return format_html(
            '<span style="background-color: #6366F1; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = "طريقة الدفع"


@admin.register(SubscriptionAuditLog)
class SubscriptionAuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action_badge', 'actor', 'target_user', 'details')
    list_filter = ('action', 'created_at')
    search_fields = (
        'target_user__username',
        'target_user__phone',
        'actor__username',
        'details'
    )
    date_hierarchy = 'created_at'
    readonly_fields = ('subscription', 'actor', 'target_user', 'action', 'details', 'created_at')

    def action_badge(self, obj):
        return format_html(
            '<span style="background-color: #0F172A; color: #fff; padding: 2px 7px; border-radius: 4px; font-size: 11px;">{}</span>',
            obj.action
        )
    action_badge.short_description = "الإجراء"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin
from .models import Halaqa, HalaqaMember, HalaqaSchedule, JoinRequest


class HalaqaMemberInline(admin.TabularInline):
    model = HalaqaMember
    extra = 1
    autocomplete_fields = ['user']


class HalaqaScheduleInline(admin.TabularInline):
    model = HalaqaSchedule
    extra = 1


@admin.register(Halaqa)
class HalaqaAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'visibility', 'owner', 'created_at')
    list_filter = ('gender', 'visibility', 'created_at')
    search_fields = ('name', 'description', 'owner__username', 'owner__first_name', 'owner__phone')
    inlines = [HalaqaMemberInline, HalaqaScheduleInline]


@admin.register(HalaqaMember)
class HalaqaMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'halaqa', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'user__first_name', 'user__phone', 'halaqa__name')


@admin.register(HalaqaSchedule)
class HalaqaScheduleAdmin(admin.ModelAdmin):
    list_display = ('halaqa', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week',)


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'halaqa', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__phone', 'halaqa__name')

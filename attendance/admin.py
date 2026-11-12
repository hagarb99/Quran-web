from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status', 'is_deleted', 'created_at')
    list_filter = ('status', 'is_deleted', 'session__date')
    search_fields = ('student__username', 'student__phone', 'session__title', 'session__halaqa__name')

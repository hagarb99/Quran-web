from django.contrib import admin
from .models import Recitation


@admin.register(Recitation)
class RecitationAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'rating', 'new_memorization', 'is_deleted', 'created_at')
    list_filter = ('rating', 'is_deleted', 'session__date')
    search_fields = ('student__username', 'student__phone', 'session__title')

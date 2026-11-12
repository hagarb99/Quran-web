from django.contrib import admin
from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'halaqa', 'date', 'start_time', 'status', 'is_deleted')
    list_filter = ('status', 'is_deleted', 'date')
    search_fields = ('title', 'halaqa__name')
    date_hierarchy = 'date'

from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_type', 'halaqa', 'participant1', 'participant2', 'updated_at')
    list_filter = ('chat_type', 'created_at')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'content', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'sender__username', 'sender__phone')

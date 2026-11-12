from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_SESSION_CREATED = 'SESSION_CREATED'
    TYPE_SESSION_UPDATED = 'SESSION_UPDATED'
    TYPE_SESSION_CANCELLED = 'SESSION_CANCELLED'
    TYPE_CHAT_MESSAGE = 'CHAT_MESSAGE'
    TYPE_JOIN_REQUEST = 'JOIN_REQUEST'
    TYPE_REQUEST_STATUS = 'REQUEST_STATUS'
    TYPE_GENERAL = 'GENERAL'

    TYPE_CHOICES = [
        (TYPE_SESSION_CREATED, 'جلسة جديدة'),
        (TYPE_SESSION_UPDATED, 'تعديل موعد الجلسة'),
        (TYPE_SESSION_CANCELLED, 'إلغاء جلسة'),
        (TYPE_CHAT_MESSAGE, 'رسالة محادثة جديدة'),
        (TYPE_JOIN_REQUEST, 'طلب انضمام'),
        (TYPE_REQUEST_STATUS, 'حالة طلب الانضمام'),
        (TYPE_GENERAL, 'إشعار عام'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="المستلم"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='caused_notifications',
        verbose_name="الفاعل"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_GENERAL,
        verbose_name="نوع الإشعار"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان الإشعار")
    message = models.TextField(verbose_name="نص الإشعار")
    link = models.CharField(max_length=255, blank=True, verbose_name="الرابط المرتبط")
    is_read = models.BooleanField(default=False, db_index=True, verbose_name="تمت القراءة")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="وقت الإشعار")

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ['-created_at']

    def __str__(self):
        return f"إشعار إلى {self.recipient.display_name}: {self.title}"


def notify_user(recipient, title, message, link='', actor=None, notification_type=Notification.TYPE_GENERAL):
    """
    Utility helper to create an in-app notification.
    """
    if recipient and (not actor or recipient.id != actor.id):
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            title=title,
            message=message,
            link=link,
            notification_type=notification_type
        )
    return None

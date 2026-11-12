from django.db import models
from django.conf import settings
from django.db.models import Q
from halaqat.models import Halaqa


class Conversation(models.Model):
    TYPE_GROUP = 'GROUP'
    TYPE_DIRECT = 'DIRECT'

    TYPE_CHOICES = [
        (TYPE_GROUP, 'محادثة جماعية للحلقة'),
        (TYPE_DIRECT, 'محادثة مباشرة خاصة'),
    ]

    chat_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_GROUP, verbose_name="نوع المحادثة")
    halaqa = models.OneToOneField(
        Halaqa,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_room',
        verbose_name="الحلقة التابعة لها"
    )
    participant1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='direct_chats_as_p1',
        verbose_name="الطرف الأول"
    )
    participant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='direct_chats_as_p2',
        verbose_name="الطرف الثاني"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ آخر نشاط")

    class Meta:
        verbose_name = "محادثة"
        verbose_name_plural = "المحادثات"
        ordering = ['-updated_at']

    def __str__(self):
        if self.chat_type == self.TYPE_GROUP and self.halaqa:
            return f"محادثة حلقة: {self.halaqa.name}"
        if self.participant1 and self.participant2:
            return f"محادثة خاصة: {self.participant1.display_name} و {self.participant2.display_name}"
        return f"محادثة رقم {self.id}"

    def can_access(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_platform_admin:
            return True
        if self.chat_type == self.TYPE_GROUP and self.halaqa:
            return self.halaqa.is_owner(user) or self.halaqa.members.filter(user=user).exists()
        if self.chat_type == self.TYPE_DIRECT:
            return user.id in (self.participant1_id, self.participant2_id)
        return False

    def get_title_for_user(self, user):
        if self.chat_type == self.TYPE_GROUP and self.halaqa:
            return self.halaqa.name
        if self.chat_type == self.TYPE_DIRECT:
            other = self.get_other_participant(user)
            return other.display_name if other else "مستخدم"
        return "محادثة"

    def get_other_participant(self, user):
        if self.chat_type != self.TYPE_DIRECT:
            return None
        if user.id == self.participant1_id:
            return self.participant2
        return self.participant1


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="المحادثة"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name="المرسل"
    )
    content = models.TextField(verbose_name="نص الرسالة")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="وقت الإرسال")

    class Meta:
        verbose_name = "رسالة"
        verbose_name_plural = "الرسائل"
        ordering = ['created_at']

    def __str__(self):
        return f"رسالة من {self.sender.display_name} في ({self.created_at.strftime('%H:%M')})"

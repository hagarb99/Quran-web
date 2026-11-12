from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember
from .models import Conversation, Message


class ChatAccessAndMessagingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user_chat1',
            email='c1@example.com',
            phone='0599999991',
            password='Password123!',
            gender=User.GENDER_MALE
        )
        self.user2 = User.objects.create_user(
            username='user_chat2',
            email='c2@example.com',
            phone='0599999992',
            password='Password123!',
            gender=User.GENDER_MALE
        )
        self.outsider = User.objects.create_user(
            username='user_chat3',
            email='c3@example.com',
            phone='0599999993',
            password='Password123!',
            gender=User.GENDER_MALE
        )

        # Halaqa group chat
        self.halaqa = Halaqa.objects.create(name='حلقة الشات', gender=Halaqa.GENDER_MALE, owner=self.user1)
        HalaqaMember.objects.create(halaqa=self.halaqa, user=self.user1, role=HalaqaMember.ROLE_OWNER)
        HalaqaMember.objects.create(halaqa=self.halaqa, user=self.user2, role=HalaqaMember.ROLE_STUDENT)
        self.group_chat = Conversation.objects.create(chat_type=Conversation.TYPE_GROUP, halaqa=self.halaqa)

        # Direct chat
        self.direct_chat = Conversation.objects.create(
            chat_type=Conversation.TYPE_DIRECT,
            participant1=self.user1,
            participant2=self.user2
        )

    def test_group_chat_permission_control(self):
        """Ensure users only access conversations they belong to."""
        # Member user2 can access
        self.assertTrue(self.group_chat.can_access(self.user2))
        # Outsider user3 cannot access
        self.assertFalse(self.group_chat.can_access(self.outsider))

        # Test view returns 403 Forbidden for outsider
        self.client.login(username='user_chat3', password='Password123!')
        response = self.client.get(reverse('chat:conversation_detail', kwargs={'pk': self.group_chat.id}))
        self.assertEqual(response.status_code, 403)

    def test_direct_chat_messaging_and_polling(self):
        # User1 sends a message
        self.client.login(username='user_chat1', password='Password123!')
        send_url = reverse('chat:send_message', kwargs={'pk': self.direct_chat.id})
        response = self.client.post(send_url, {'content': 'السلام عليكم ورحمة الله'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        msg_id = data['message']['id']

        # User2 polls for messages after id 0
        self.client.login(username='user_chat2', password='Password123!')
        poll_url = f"{reverse('chat:poll_messages', kwargs={'pk': self.direct_chat.id})}?after=0"
        poll_response = self.client.get(poll_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(poll_response.status_code, 200)
        messages_received = poll_response.json()['messages']
        self.assertEqual(len(messages_received), 1)
        self.assertEqual(messages_received[0]['content'], 'السلام عليكم ورحمة الله')
        self.assertFalse(messages_received[0]['is_me'])  # For user2, message was sent by user1

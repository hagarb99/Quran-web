from django.test import TestCase, Client
from django.urls import reverse
from .models import User


class AccountsSecurityAndAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='teacher1',
            email='teacher1@example.com',
            phone='0501112222',
            password='SecurePassword123!',
            gender=User.GENDER_MALE,
            role=User.ROLE_TEACHER,
            first_name='أحمد',
            last_name='المعلم'
        )

    def test_phone_or_email_login(self):
        # 1. Login with username
        logged_in = self.client.login(username='teacher1', password='SecurePassword123!')
        self.assertTrue(logged_in)
        self.client.logout()

        # 2. Login with email
        logged_in = self.client.login(username='teacher1@example.com', password='SecurePassword123!')
        self.assertTrue(logged_in)
        self.client.logout()

        # 3. Login with phone
        logged_in = self.client.login(username='0501112222', password='SecurePassword123!')
        self.assertTrue(logged_in)

    def test_suspended_user_cannot_login(self):
        self.user.is_suspended = True
        self.user.save()

        logged_in = self.client.login(username='0501112222', password='SecurePassword123!')
        self.assertFalse(logged_in)

    def test_security_phone_number_cannot_be_password(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'خالد',
            'last_name': 'القارئ',
            'username': 'khaled_qari',
            'email': 'khaled@example.com',
            'phone': '0555555555',
            'gender': User.GENDER_MALE,
            'role': User.ROLE_STUDENT,
            'password': '0555555555',
            'password_confirm': '0555555555',
        })
        self.assertFormError(response.context['form'], 'password', "لأسباب أمنية، لا يمكن استخدام رقم الهاتف ككلمة مرور.")
        self.assertFalse(User.objects.filter(username='khaled_qari').exists())

    def test_unique_phone_and_email(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'محمد',
            'last_name': 'المعلم',
            'username': 'mohamed2',
            'email': 'teacher1@example.com',  # duplicate email
            'phone': '0501112222',  # duplicate phone
            'gender': User.GENDER_MALE,
            'role': User.ROLE_STUDENT,
            'password': 'DifferentPass123!',
            'password_confirm': 'DifferentPass123!',
        })
        self.assertTrue(response.context['form'].has_error('email'))
        self.assertTrue(response.context['form'].has_error('phone'))

import os
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_STUDENT = 'STUDENT'
    ROLE_TEACHER = 'TEACHER'
    ROLE_ADMIN = 'ADMIN'
    
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'طالب'),
        (ROLE_TEACHER, 'معلم'),
        (ROLE_ADMIN, 'مسؤول النظام'),
    ]

    GENDER_MALE = 'MALE'
    GENDER_FEMALE = 'FEMALE'
    
    GENDER_CHOICES = [
        (GENDER_MALE, 'ذكر'),
        (GENDER_FEMALE, 'أنثى'),
    ]

    phone = models.CharField(max_length=20, unique=True, verbose_name="رقم الهاتف", db_index=True)
    email = models.EmailField(unique=True, verbose_name="البريد الإلكتروني", db_index=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="الجنس")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT, verbose_name="نوع الحساب")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="الصورة الشخصية")
    bio = models.TextField(blank=True, null=True, verbose_name="نبذة شخصية")
    is_suspended = models.BooleanField(default=False, verbose_name="معلق الحساب")

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
        ordering = ['-date_joined']

    def __str__(self):
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def display_name(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    @property
    def is_platform_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser or self.is_staff

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        min_length=6
    )
    password_confirm = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        min_length=6
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'gender', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الأول'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم العائلة'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم (بالإنجليزية)'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@domain.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '05xxxxxxxx أو +966...'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'اسم العائلة',
            'username': 'اسم المستخدم',
            'email': 'البريد الإلكتروني',
            'phone': 'رقم الهاتف',
            'gender': 'الجنس',
            'role': 'نوع الحساب',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # In MVP registration, users can register as Student or Teacher
        self.fields['role'].choices = [
            (User.ROLE_STUDENT, 'طالب'),
            (User.ROLE_TEACHER, 'معلم'),
        ]

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise ValidationError("رقم الهاتف مطلوب.")
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("رقم الهاتف مسجل مسبقاً لمستخدم آخر.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("البريد الإلكتروني مطلوب.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("البريد الإلكتروني مسجل مسبقاً لمستخدم آخر.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        phone = cleaned_data.get('phone')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "كلمتا المرور غير متطابقتين.")

        # Security check: Never use phone numbers as passwords
        if password and phone and (password == phone or phone in password):
            self.add_error('password', "لأسباب أمنية، لا يمكن استخدام رقم الهاتف ككلمة مرور.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    login_field = forms.CharField(
        label="اسم المستخدم / البريد / رقم الهاتف",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'أدخل اسم المستخدم أو البريد أو الهاتف'})
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'avatar', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'اكتب نبذة عن مؤهلاتك أو أهدافك القرآنيّة...'}),
        }
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'اسم العائلة',
            'email': 'البريد الإلكتروني',
            'phone': 'رقم الهاتف',
            'avatar': 'الصورة الشخصية',
            'bio': 'نبذة شخصية',
        }

    def __init__(self, *args, **kwargs):
        self.instance_user = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if User.objects.filter(phone=phone).exclude(pk=self.instance_user.pk).exists():
            raise ValidationError("رقم الهاتف مستخدم بالفعل بحساب آخر.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance_user.pk).exists():
            raise ValidationError("البريد الإلكتروني مستخدم بالفعل بحساب آخر.")
        return email


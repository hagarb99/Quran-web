from django import forms
from django.core.exceptions import ValidationError
from .models import Halaqa, HalaqaSchedule, HalaqaMember
from accounts.models import User


class HalaqaForm(forms.ModelForm):
    class Meta:
        model = Halaqa
        fields = ['name', 'description', 'gender', 'visibility']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: حلقة الإمام نافع لتحفيظ القرآن'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'اكتب وصفاً مختصراً لأهداف الحلقة ومستواها...'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'اسم الحلقة',
            'description': 'وصف الحلقة',
            'gender': 'الفئة المستهدفة (الجنس)',
            'visibility': 'مستوى الظهور والخصوصية',
        }


class HalaqaScheduleForm(forms.ModelForm):
    class Meta:
        model = HalaqaSchedule
        fields = ['day_of_week', 'start_time', 'end_time', 'notes']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ملاحظات اختيارية'}),
        }
        labels = {
            'day_of_week': 'اليوم الأسبوعي',
            'start_time': 'وقت البدء',
            'end_time': 'وقت الانتهاء',
            'notes': 'ملاحظات الموعد',
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', "وقت الانتهاء يجب أن يكون بعد وقت البدء.")
        return cleaned_data


class AddMemberByPhoneForm(forms.Form):
    phone = forms.CharField(
        label="رقم هاتف المستخدم المسجل",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'أدخل رقم الهاتف المسجل في المنصة'})
    )
    role = forms.ChoiceField(
        label="دور العضوية في الحلقة",
        choices=[
            (HalaqaMember.ROLE_STUDENT, 'طالب'),
            (HalaqaMember.ROLE_TEACHER, 'معلم'),
            (HalaqaMember.ROLE_ASSISTANT, 'مساعد'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    can_manage_sessions = forms.BooleanField(label="صلاحية إدارة وجدولة الجلسات", required=False, initial=True)
    can_record_attendance = forms.BooleanField(label="صلاحية رصد الحضور والغياب", required=False, initial=True)
    can_record_recitation = forms.BooleanField(label="صلاحية تدوين التسميع والواجبات", required=False, initial=True)
    can_manage_members = forms.BooleanField(label="صلاحية إضافة وقبول الأعضاء", required=False, initial=False)


class UpdateMemberRoleForm(forms.ModelForm):
    class Meta:
        model = HalaqaMember
        fields = ['role', 'can_manage_sessions', 'can_record_attendance', 'can_record_recitation', 'can_manage_members']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'can_manage_sessions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_record_attendance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_record_recitation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_members': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'role': 'دور العضوية',
            'can_manage_sessions': 'إدارة الجلسات',
            'can_record_attendance': 'تسجيل الحضور',
            'can_record_recitation': 'تسجيل التسميع',
            'can_manage_members': 'إدارة الأعضاء والطلبات',
        }


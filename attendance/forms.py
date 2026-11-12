from django import forms
from .models import Attendance


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'status', 'notes']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ملاحظات اختيارية (مثال: تأخر 10 دقائق)'}),
        }
        labels = {
            'student': 'الطالب',
            'status': 'حالة الحضور',
            'notes': 'ملاحظات',
        }


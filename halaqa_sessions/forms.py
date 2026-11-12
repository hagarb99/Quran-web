from django import forms
from .models import Session


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['title', 'date', 'start_time', 'end_time', 'meet_url', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: تسميع سورة البقرة وتجويد أحكام النون'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'meet_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://meet.google.com/xxx-xxxx-xxx'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ملاحظات أو توجيهات للطلاب بخصوص الجلسة...'}),
        }
        labels = {
            'title': 'عنوان الجلسة',
            'date': 'تاريخ انعقاد الجلسة',
            'start_time': 'وقت البدء',
            'end_time': 'وقت الانتهاء (اختياري)',
            'meet_url': 'رابط Google Meet (اختياري)',
            'notes': 'ملاحظات الجلسة',
        }


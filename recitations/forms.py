from django import forms
from .models import Recitation


class RecitationForm(forms.ModelForm):
    class Meta:
        model = Recitation
        fields = [
            'student',
            'new_memorization',
            'near_revision',
            'far_revision',
            'rating',
            'teacher_notes',
            'next_assignment',
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'new_memorization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: سورة النبأ من 1 إلى 20'}),
            'near_revision': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: سورة المرسلات كاملة'}),
            'far_revision': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: جزء عم كاملاً'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'teacher_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توجيهات التجويد، مخارج الحروف، التنبيهات...'}),
            'next_assignment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'الواجب المطلوب للجلسة القادمة...'}),
        }
        labels = {
            'student': 'الطالب',
            'new_memorization': 'الحفظ الجديد',
            'near_revision': 'المراجعة القريبة',
            'far_revision': 'المراجعة البعيدة',
            'rating': 'مستوى الأداء والتقييم',
            'teacher_notes': 'ملاحظات المعلم',
            'next_assignment': 'الواجب القادم (اختياري)',
        }


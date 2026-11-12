from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time, timedelta
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember, HalaqaSchedule
from halaqa_sessions.models import Session
from attendance.models import Attendance
from recitations.models import Recitation
from chat.models import Conversation, Message
from notifications.models import Notification


class Command(BaseCommand):
    help = "Seeds initial demo data for testing the Quran Halaqat Platform"

    def handle(self, *args, **options):
        self.stdout.write("جاري إنشاء البيانات التجريبية للمنصة...")

        # 1. Users
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@quran.com',
                'phone': '0500000000',
                'role': User.ROLE_ADMIN,
                'gender': User.GENDER_MALE,
                'first_name': 'مدير',
                'last_name': 'المنصة',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin.set_password('Admin@123456')
        admin.save()

        teacher_m, _ = User.objects.get_or_create(
            username='teacher_ahmed',
            defaults={
                'email': 'ahmed@quran.com',
                'phone': '0511111111',
                'role': User.ROLE_TEACHER,
                'gender': User.GENDER_MALE,
                'first_name': 'أحمد',
                'last_name': 'الغامدي',
                'bio': 'إجازة في القراءات العشر بالسند المتصل إلى رسول الله ﷺ، خبرة 15 عاماً في الإقراء والتحفيظ.'
            }
        )
        teacher_m.set_password('Teacher@123456')
        teacher_m.save()

        teacher_f, _ = User.objects.get_or_create(
            username='teacher_khadija',
            defaults={
                'email': 'khadija@quran.com',
                'phone': '0522222222',
                'role': User.ROLE_TEACHER,
                'gender': User.GENDER_FEMALE,
                'first_name': 'خديجة',
                'last_name': 'الأنصاري',
                'bio': 'معلمة ومجازة برواية حفص عن عاصم، مشرفة حلقات التجويد والإتقان النسائية.'
            }
        )
        teacher_f.set_password('Teacher@123456')
        teacher_f.save()

        student_m, _ = User.objects.get_or_create(
            username='student_omar',
            defaults={
                'email': 'omar@quran.com',
                'phone': '0533333333',
                'role': User.ROLE_STUDENT,
                'gender': User.GENDER_MALE,
                'first_name': 'عمر',
                'last_name': 'سالم',
                'bio': 'طالب مجتهد يحفظ 10 أجزاء ويطمح لإتمام حفظ القرآن الكريم كاملاً.'
            }
        )
        student_m.set_password('Student@123456')
        student_m.save()

        student_f, _ = User.objects.get_or_create(
            username='student_maryam',
            defaults={
                'email': 'maryam@quran.com',
                'phone': '0544444444',
                'role': User.ROLE_STUDENT,
                'gender': User.GENDER_FEMALE,
                'first_name': 'مريم',
                'last_name': 'حسن',
                'bio': 'طالبة مهتمة بضبط المتشابهات والتجويد العملي.'
            }
        )
        student_f.set_password('Student@123456')
        student_f.save()

        self.stdout.write(self.style.SUCCESS("✓ تم إنشاء المستخدمين بنجاح."))

        # 2. Halaqat
        # Male Public Halaqa
        halaqa_m, _ = Halaqa.objects.get_or_create(
            name='حلقة الإمام عاصم (رجال)',
            defaults={
                'description': 'حلقة عامة مخصصة لحفظ وضبط وتجويد القرآن الكريم للذكور، تعتمد المنهجية التراكمية في المراجعة والتسميع اليومي.',
                'gender': Halaqa.GENDER_MALE,
                'visibility': Halaqa.VISIBILITY_PUBLIC,
                'owner': teacher_m
            }
        )
        HalaqaMember.objects.get_or_create(
            halaqa=halaqa_m,
            user=teacher_m,
            defaults={
                'role': HalaqaMember.ROLE_OWNER,
                'can_manage_sessions': True,
                'can_record_attendance': True,
                'can_record_recitation': True,
                'can_manage_members': True,
            }
        )
        HalaqaMember.objects.get_or_create(
            halaqa=halaqa_m,
            user=student_m,
            defaults={'role': HalaqaMember.ROLE_STUDENT}
        )
        conv_m, _ = Conversation.objects.get_or_create(
            halaqa=halaqa_m,
            defaults={'chat_type': Conversation.TYPE_GROUP}
        )

        # Female Public Halaqa
        halaqa_f, _ = Halaqa.objects.get_or_create(
            name='حلقة أم المؤمنين خديجة (نساء)',
            defaults={
                'description': 'حلقة عامة للفتيات والسيدات لحفظ القرآن الكريم وتصحيح التلاوة وتدارس أحكام التجويد النظرية والتطبيقية.',
                'gender': Halaqa.GENDER_FEMALE,
                'visibility': Halaqa.VISIBILITY_PUBLIC,
                'owner': teacher_f
            }
        )
        HalaqaMember.objects.get_or_create(
            halaqa=halaqa_f,
            user=teacher_f,
            defaults={
                'role': HalaqaMember.ROLE_OWNER,
                'can_manage_sessions': True,
                'can_record_attendance': True,
                'can_record_recitation': True,
                'can_manage_members': True,
            }
        )
        HalaqaMember.objects.get_or_create(
            halaqa=halaqa_f,
            user=student_f,
            defaults={'role': HalaqaMember.ROLE_STUDENT}
        )
        conv_f, _ = Conversation.objects.get_or_create(
            halaqa=halaqa_f,
            defaults={'chat_type': Conversation.TYPE_GROUP}
        )

        # Schedules
        HalaqaSchedule.objects.get_or_create(
            halaqa=halaqa_m,
            day_of_week=0,  # Saturday
            start_time=time(17, 0),
            end_time=time(18, 30),
            defaults={'notes': 'تسميع ومراجعة الحفظ الجديد'}
        )
        HalaqaSchedule.objects.get_or_create(
            halaqa=halaqa_m,
            day_of_week=2,  # Monday
            start_time=time(17, 0),
            end_time=time(18, 30),
            defaults={'notes': 'مراجعة قريبة وبعيدة'}
        )

        self.stdout.write(self.style.SUCCESS("✓ تم إنشاء الحلقات وجداول المواعيد والأعضاء."))

        # 3. Sessions
        today = timezone.now().date()
        s1, _ = Session.objects.get_or_create(
            halaqa=halaqa_m,
            title='جلسة افتتاحية وتسميع سورة النبأ',
            date=today - timedelta(days=2),
            start_time=time(17, 0),
            defaults={
                'end_time': time(18, 30),
                'meet_url': 'https://meet.google.com/abc-defg-hij',
                'status': Session.STATUS_COMPLETED,
                'notes': 'تم ضبط مخارج الحروف والمدود في أوائل جزء عم.',
                'created_by': teacher_m,
                'completed_at': timezone.now() - timedelta(days=2, hours=1),
                'completed_by': teacher_m
            }
        )

        s2, _ = Session.objects.get_or_create(
            halaqa=halaqa_m,
            title='تسميع سورة النازعات والمراجعة الأسبوعية',
            date=today + timedelta(days=1),
            start_time=time(17, 0),
            defaults={
                'end_time': time(18, 30),
                'meet_url': 'https://meet.google.com/qwe-rtyu-iop',
                'status': Session.STATUS_SCHEDULED,
                'notes': 'يرجى التحضير الجيد والمراجعة من المصحف المرتل.',
                'created_by': teacher_m
            }
        )

        # Attendance & Recitation for Session 1
        att, _ = Attendance.objects.get_or_create(
            session=s1,
            student=student_m,
            defaults={
                'status': Attendance.STATUS_PRESENT,
                'notes': 'حضور مبكر وتفاعل ممتاز',
                'created_by': teacher_m
            }
        )

        rec, _ = Recitation.objects.get_or_create(
            session=s1,
            student=student_m,
            defaults={
                'new_memorization': 'سورة النبأ من 1 إلى 30',
                'near_revision': 'سورة المرسلات كاملة',
                'far_revision': 'سورة الإنسان',
                'rating': Recitation.RATING_MUMTAZ,
                'teacher_notes': 'أداء رائع وصوت ندي مع مراعاة الغنن وأحكام النون الساكنة.',
                'next_assignment': 'إتمام سورة النبأ وحفظ أول 15 آية من سورة النازعات.',
                'created_by': teacher_m
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ تم إنشاء الجلسات وسجلات الحضور والتسميع."))

        # 4. Chat Messages
        if conv_m.messages.count() == 0:
            Message.objects.create(
                conversation=conv_m,
                sender=teacher_m,
                content='السلام عليكم ورحمة الله وبركاته، مرحباً بكم جميعاً في حلقة الإمام عاصم المباركة.'
            )
            Message.objects.create(
                conversation=conv_m,
                sender=student_m,
                content='وعليكم السلام ورحمة الله وبركاته يا شيخنا الفاضل، نفع الله بكم وبارك في جهودكم.'
            )

        # Direct Chat between Teacher Ahmed and Student Omar
        direct_conv, _ = Conversation.objects.get_or_create(
            chat_type=Conversation.TYPE_DIRECT,
            participant1=teacher_m,
            participant2=student_m
        )
        if direct_conv.messages.count() == 0:
            Message.objects.create(
                conversation=direct_conv,
                sender=teacher_m,
                content='أهلاً بك يا عمر، استمر على هذا المستوى المتميز في الحفظ.'
            )
            Message.objects.create(
                conversation=direct_conv,
                sender=student_m,
                content='جزاكم الله كل خير شيخنا، سأجتهد في مراجعة الواجب القادم بإذن الله.'
            )

        # 5. In-app Notifications
        Notification.objects.get_or_create(
            recipient=student_m,
            title=f"جلسة جديدة في حلقة {halaqa_m.name}",
            defaults={
                'message': f"تمت جدولة جلسة '{s2.title}' يوم {s2.date} الساعة 17:00.",
                'link': f"/sessions/{s2.id}/",
                'notification_type': Notification.TYPE_SESSION_CREATED,
                'actor': teacher_m
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ تم إدراج الرسائل والمحادثات والتنبيهات."))
        self.stdout.write(self.style.SUCCESS("تم تجهيز البيانات التجريبية بنجاح!"))


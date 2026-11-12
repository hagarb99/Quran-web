from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Session
from .forms import SessionForm
from halaqat.models import Halaqa, HalaqaMember
from attendance.models import Attendance
from recitations.models import Recitation
from notifications.models import notify_user, Notification


@login_required
def session_create_view(request, halaqa_id):
    halaqa = get_object_or_404(Halaqa, pk=halaqa_id)
    if not halaqa.can_manage_sessions(request.user):
        messages.error(request, "ليست لديك صلاحية إنشاء جلسات في هذه الحلقة.")
        return redirect('halaqat:detail', pk=halaqa_id)

    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.halaqa = halaqa
            session.created_by = request.user
            session.save()

            # Rule H: Notify halaqa members of new session
            for member in halaqa.members.select_related('user').all():
                if member.user != request.user:
                    notify_user(
                        recipient=member.user,
                        actor=request.user,
                        title=f"جلسة جديدة في حلقة {halaqa.name}",
                        message=f"تمت جدولة جلسة جديدة '{session.title}' يوم {session.date} الساعة {session.start_time.strftime('%H:%M')}.",
                        link=f"/sessions/{session.id}/",
                        notification_type=Notification.TYPE_SESSION_CREATED
                    )

            messages.success(request, f"تم إنشاء الجلسة '{session.title}' بنجاح.")
            return redirect('halaqa_sessions:detail', pk=session.pk)
        else:
            messages.error(request, "يرجى تصحيح الأخطاء في نموذج الجلسة.")
    else:
        form = SessionForm(initial={'date': timezone.now().date()})

    return render(request, 'halaqa_sessions/session_form.html', {'form': form, 'halaqa': halaqa, 'is_edit': False})


@login_required
def session_detail_view(request, pk):
    session = get_object_or_404(Session.all_objects.select_related('halaqa', 'created_by', 'updated_by', 'completed_by', 'reopened_by'), pk=pk)
    halaqa = session.halaqa

    # Check access permission
    member = halaqa.get_member(request.user)
    is_owner = halaqa.is_owner(request.user)
    is_admin = request.user.is_platform_admin

    if not (member or is_owner or is_admin):
        messages.error(request, "لا يمكنك عرض تفاصيل جلسة في حلقة لست عضواً بها.")
        return redirect('halaqat:my_halaqat')

    can_manage_sessions = halaqa.can_manage_sessions(request.user)
    can_record_attendance = halaqa.can_record_attendance(request.user)
    can_record_recitation = halaqa.can_record_recitation(request.user)

    # Get all active students enrolled in this halaqa
    student_members = halaqa.members.filter(role=HalaqaMember.ROLE_STUDENT).select_related('user').order_by('user__first_name')

    # Fetch active attendances and recitations for this session
    attendances_dict = {
        att.student_id: att for att in Attendance.objects.filter(session=session).select_related('student')
    }
    recitations_dict = {
        rec.student_id: rec for rec in Recitation.objects.filter(session=session).select_related('student')
    }

    # Build student roster with attendance & recitation data
    student_roster = []
    for sm in student_members:
        u = sm.user
        student_roster.append({
            'user': u,
            'attendance': attendances_dict.get(u.id),
            'recitation': recitations_dict.get(u.id),
        })

    context = {
        'session': session,
        'halaqa': halaqa,
        'can_manage_sessions': can_manage_sessions,
        'can_record_attendance': can_record_attendance,
        'can_record_recitation': can_record_recitation,
        'student_roster': student_roster,
        'is_student': member and member.role == HalaqaMember.ROLE_STUDENT,
        'my_attendance': attendances_dict.get(request.user.id),
        'my_recitation': recitations_dict.get(request.user.id),
    }
    return render(request, 'halaqa_sessions/session_detail.html', context)


@login_required
def session_edit_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    halaqa = session.halaqa

    if not halaqa.can_manage_sessions(request.user):
        messages.error(request, "ليست لديك صلاحية تعديل هذه الجلسة.")
        return redirect('halaqa_sessions:detail', pk=pk)

    old_date = session.date
    old_time = session.start_time

    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            updated_session = form.save(commit=False)
            updated_session.updated_by = request.user
            updated_session.save()

            # If date or time changed, notify members
            if updated_session.date != old_date or updated_session.start_time != old_time:
                for member in halaqa.members.select_related('user').all():
                    if member.user != request.user:
                        notify_user(
                            recipient=member.user,
                            actor=request.user,
                            title=f"تعديل موعد جلسة: {updated_session.title}",
                            message=f"تم تعديل موعد جلسة '{updated_session.title}' إلى {updated_session.date} الساعة {updated_session.start_time.strftime('%H:%M')}.",
                            link=f"/sessions/{updated_session.id}/",
                            notification_type=Notification.TYPE_SESSION_UPDATED
                        )

            messages.success(request, "تم حفظ تعديلات الجلسة بنجاح.")
            return redirect('halaqa_sessions:detail', pk=pk)
        else:
            messages.error(request, "يرجى تصحيح الأخطاء.")
    else:
        form = SessionForm(instance=session)

    return render(request, 'halaqa_sessions/session_form.html', {'form': form, 'halaqa': halaqa, 'is_edit': True, 'session': session})


@login_required
def session_action_view(request, pk, action):
    session = get_object_or_404(Session, pk=pk)
    halaqa = session.halaqa

    if not halaqa.can_manage_sessions(request.user):
        messages.error(request, "ليست لديك صلاحية تنفيذ هذا الإجراء على الجلسة.")
        return redirect('halaqa_sessions:detail', pk=pk)

    if action == 'start':
        session.status = Session.STATUS_IN_PROGRESS
        session.updated_by = request.user
        session.save()

        # Notify all halaqa members (students, assistants, etc.)
        for member in halaqa.members.select_related('user').all():
            if member.user != request.user:
                meet_msg = " ورابط Google Meet متاح الآن داخل الجلسة." if session.meet_url else "."
                notify_user(
                    recipient=member.user,
                    actor=request.user,
                    title=f"بدأت الجلسة الآن: {session.title} 🔴",
                    message=f"بدأ المعلم {request.user.display_name} جلسة '{session.title}' في حلقة '{halaqa.name}'{meet_msg}",
                    link=f"/sessions/{session.id}/",
                    notification_type=Notification.TYPE_SESSION_STARTED
                )

        messages.success(request, f"بدأت الجلسة '{session.title}' الآن (حالة جارية)، وتم إرسال تنبيه مباشر لجميع الطلاب.")

    elif action == 'complete':
        try:
            session.mark_completed(request.user)
            messages.success(request, f"تم تعليم الجلسة '{session.title}' كمكتملة.")
        except ValueError as e:
            messages.error(request, str(e))

    elif action == 'reopen':
        try:
            session.reopen(request.user)
            messages.info(request, f"تمت إعادة فتح الجلسة '{session.title}'؛ أصبحت حالتها جارية الآن.")
        except ValueError as e:
            messages.error(request, str(e))

    elif action == 'cancel':
        session.cancel(request.user)
        # Notify members
        for member in halaqa.members.select_related('user').all():
            if member.user != request.user:
                notify_user(
                    recipient=member.user,
                    actor=request.user,
                    title=f"إلغاء جلسة: {session.title}",
                    message=f"نحيطكم علماً بأنه تم إلغاء جلسة '{session.title}' التي كانت مقررة بتاريخ {session.date}.",
                    link=f"/sessions/{session.id}/",
                    notification_type=Notification.TYPE_SESSION_CANCELLED
                )
        messages.warning(request, f"تم إلغاء الجلسة '{session.title}'.")

    return redirect('halaqa_sessions:detail', pk=pk)


@login_required
def session_delete_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    halaqa = session.halaqa

    if not halaqa.can_manage_sessions(request.user):
        messages.error(request, "ليست لديك صلاحية حذف الجلسة.")
        return redirect('halaqa_sessions:detail', pk=pk)

    if request.method == 'POST':
        session.soft_delete(request.user)
        messages.success(request, f"تم حذف الجلسة '{session.title}' (حذف مؤقت).")
        return redirect('halaqat:detail', pk=halaqa.pk)

    return render(request, 'halaqa_sessions/confirm_delete_session.html', {'session': session, 'halaqa': halaqa})

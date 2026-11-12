from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Attendance
from .forms import AttendanceForm
from halaqa_sessions.models import Session
from accounts.models import User


@login_required
def record_attendance_view(request, session_id, student_id):
    session = get_object_or_404(Session, pk=session_id)
    halaqa = session.halaqa

    if not halaqa.can_record_attendance(request.user):
        messages.error(request, "ليست لديك صلاحية تسجيل الحضور والغياب.")
        return redirect('halaqa_sessions:detail', pk=session_id)

    student = get_object_or_404(User, pk=student_id)

    # Check if active attendance already exists
    attendance = Attendance.objects.filter(session=session, student=student).first()

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '').strip()

        if status not in [s[0] for s in Attendance.STATUS_CHOICES]:
            messages.error(request, "حالة الحضور المحددة غير صحيحة.")
            return redirect('halaqa_sessions:detail', pk=session_id)

        if attendance:
            attendance.status = status
            attendance.notes = notes
            attendance.updated_by = request.user
            attendance.save()
            messages.success(request, f"تم تحديث حضور {student.display_name} إلى: {attendance.get_status_display()}.")
        else:
            attendance = Attendance.objects.create(
                session=session,
                student=student,
                status=status,
                notes=notes,
                created_by=request.user
            )
            messages.success(request, f"تم تسجيل حضور {student.display_name}: {attendance.get_status_display()}.")

        return redirect('halaqa_sessions:detail', pk=session_id)

    context = {
        'session': session,
        'student': student,
        'attendance': attendance,
    }
    return render(request, 'attendance/record_attendance.html', context)


@login_required
def delete_attendance_view(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    session = attendance.session
    halaqa = session.halaqa

    if not halaqa.can_record_attendance(request.user):
        messages.error(request, "ليست لديك صلاحية حذف سجل الحضور.")
        return redirect('halaqa_sessions:detail', pk=session.id)

    if request.method == 'POST':
        student_name = attendance.student.display_name
        attendance.soft_delete(request.user)
        messages.success(request, f"تم حذف سجل حضور الطالب {student_name}.")
        return redirect('halaqa_sessions:detail', pk=session.id)

    return render(request, 'attendance/confirm_delete_attendance.html', {'attendance': attendance, 'session': session})

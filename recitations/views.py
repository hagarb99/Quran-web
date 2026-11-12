from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Recitation
from .forms import RecitationForm
from halaqa_sessions.models import Session
from accounts.models import User


@login_required
def record_recitation_view(request, session_id, student_id):
    session = get_object_or_404(Session, pk=session_id)
    halaqa = session.halaqa

    if not halaqa.can_record_recitation(request.user):
        messages.error(request, "ليست لديك صلاحية تسجيل درجات التسميع.")
        return redirect('halaqa_sessions:detail', pk=session_id)

    student = get_object_or_404(User, pk=student_id)
    recitation = Recitation.objects.filter(session=session, student=student).first()

    if request.method == 'POST':
        form = RecitationForm(request.POST, instance=recitation)
        if form.is_valid():
            rec_obj = form.save(commit=False)
            rec_obj.session = session
            rec_obj.student = student
            if not recitation:
                rec_obj.created_by = request.user
            else:
                rec_obj.updated_by = request.user
            rec_obj.save()
            messages.success(request, f"تم حفظ سجل تسميع الطالب {student.display_name} بنجاح.")
            return redirect('halaqa_sessions:detail', pk=session_id)
        else:
            messages.error(request, "يرجى تصحيح الأخطاء في نموذج التسميع.")
    else:
        initial = {'student': student}
        form = RecitationForm(instance=recitation, initial=initial)

    context = {
        'session': session,
        'student': student,
        'recitation': recitation,
        'form': form,
    }
    return render(request, 'recitations/record_recitation.html', context)


@login_required
def delete_recitation_view(request, pk):
    recitation = get_object_or_404(Recitation, pk=pk)
    session = recitation.session
    halaqa = session.halaqa

    if not halaqa.can_record_recitation(request.user):
        messages.error(request, "ليست لديك صلاحية حذف سجل التسميع.")
        return redirect('halaqa_sessions:detail', pk=session.id)

    if request.method == 'POST':
        student_name = recitation.student.display_name
        recitation.soft_delete(request.user)
        messages.success(request, f"تم حذف سجل تسميع الطالب {student_name}.")
        return redirect('halaqa_sessions:detail', pk=session.id)

    return render(request, 'recitations/confirm_delete_recitation.html', {'recitation': recitation, 'session': session})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from .models import Halaqa, HalaqaMember, HalaqaSchedule, JoinRequest
from .forms import HalaqaForm, HalaqaScheduleForm, AddMemberByPhoneForm, UpdateMemberRoleForm
from accounts.models import User
from chat.models import Conversation
from notifications.models import notify_user, Notification


@login_required
def my_halaqat_view(request):
    """
    Displays the user's active halaqat categorized by their role in them.
    """
    user = request.user
    
    # Halaqat where user is owner or teacher/assistant
    teaching_memberships = HalaqaMember.objects.filter(
        user=user,
        role__in=[HalaqaMember.ROLE_OWNER, HalaqaMember.ROLE_TEACHER, HalaqaMember.ROLE_ASSISTANT]
    ).select_related('halaqa')
    
    # Halaqat where user is student
    learning_memberships = HalaqaMember.objects.filter(
        user=user,
        role=HalaqaMember.ROLE_STUDENT
    ).select_related('halaqa')

    context = {
        'teaching_memberships': teaching_memberships,
        'learning_memberships': learning_memberships,
    }
    return render(request, 'halaqat/my_halaqat.html', context)


def browse_public_view(request):
    """
    Browse public halaqat.
    Rule 6: Private Halaqat must NOT appear in public browsing.
    Rule 8: Students can only view/join Halaqat matching their gender.
    """
    query = request.GET.get('q', '').strip()
    
    # Only public halaqat
    halaqat = Halaqa.objects.filter(visibility=Halaqa.VISIBILITY_PUBLIC)

    if request.user.is_authenticated:
        # If student, restrict to student's gender
        if request.user.role == User.ROLE_STUDENT:
            halaqat = halaqat.filter(gender=request.user.gender)

    if query:
        halaqat = halaqat.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # Attach membership / join status if authenticated
    user_memberships = set()
    user_pending_requests = set()
    if request.user.is_authenticated:
        user_memberships = set(
            HalaqaMember.objects.filter(user=request.user).values_list('halaqa_id', flat=True)
        )
        user_pending_requests = set(
            JoinRequest.objects.filter(user=request.user, status=JoinRequest.STATUS_PENDING).values_list('halaqa_id', flat=True)
        )

    context = {
        'halaqat': halaqat,
        'query': query,
        'user_memberships': user_memberships,
        'user_pending_requests': user_pending_requests,
    }
    return render(request, 'halaqat/browse_public.html', context)


@login_required
def create_halaqa_view(request):
    """
    Creates a new Halaqa and registers the creator as OWNER member,
    along with creating the linked group chat conversation.
    Rule: Students cannot create halaqat.
    """
    if request.user.role == User.ROLE_STUDENT and not request.user.is_platform_admin:
        messages.error(request, "عذراً، خاصية إنشاء الحلقات مخصصة للمعلمين ومشرفي المنصة فقط.")
        return redirect('halaqat:my_halaqat')

    if request.method == 'POST':
        form = HalaqaForm(request.POST)
        if form.is_valid():
            halaqa = form.save(commit=False)
            halaqa.owner = request.user
            halaqa.save()

            # Create owner membership
            HalaqaMember.objects.create(
                halaqa=halaqa,
                user=request.user,
                role=HalaqaMember.ROLE_OWNER,
                can_manage_sessions=True,
                can_record_attendance=True,
                can_record_recitation=True,
                can_manage_members=True
            )

            # Create linked group conversation
            Conversation.objects.get_or_create(
                halaqa=halaqa,
                defaults={'chat_type': Conversation.TYPE_GROUP}
            )

            messages.success(request, f"تم إنشاء الحلقة '{halaqa.name}' بنجاح!")
            return redirect('halaqat:detail', pk=halaqa.pk)
        else:
            messages.error(request, "يرجى التحقق من صحة البيانات المدخلة.")
    else:
        # Suggest matching gender by default if user has gender set
        initial = {'gender': request.user.gender} if hasattr(request.user, 'gender') else {}
        form = HalaqaForm(initial=initial)

    return render(request, 'halaqat/create_halaqa.html', {'form': form})


@login_required
def halaqa_detail_view(request, pk):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    user = request.user
    
    member = halaqa.get_member(user)
    is_owner = halaqa.is_owner(user)
    is_admin = user.is_platform_admin

    # Check access to private halaqa: only members, owner, or platform admin can view private halaqa
    if halaqa.visibility == Halaqa.VISIBILITY_PRIVATE and not (member or is_owner or is_admin):
        messages.error(request, "هذه الحلقة خاصة ولا يمكن الوصول إليها إلا للمنضمين إليها بدعوة.")
        return redirect('halaqat:my_halaqat')

    can_manage = halaqa.can_manage_halaqa(user)
    can_manage_sessions = halaqa.can_manage_sessions(user)
    can_record_attendance = halaqa.can_record_attendance(user)
    can_record_recitation = halaqa.can_record_recitation(user)

    schedules = halaqa.schedules.all()
    sessions = halaqa.sessions.all()[:10]  # active non-deleted sessions
    members = halaqa.members.select_related('user').all()
    pending_requests = halaqa.join_requests.filter(status=JoinRequest.STATUS_PENDING).select_related('user') if can_manage else []

    # Check user join status
    has_pending_request = False
    if not member and user.is_authenticated:
        has_pending_request = halaqa.join_requests.filter(user=user, status=JoinRequest.STATUS_PENDING).exists()

    context = {
        'halaqa': halaqa,
        'member': member,
        'can_manage': can_manage,
        'can_manage_sessions': can_manage_sessions,
        'can_record_attendance': can_record_attendance,
        'can_record_recitation': can_record_recitation,
        'schedules': schedules,
        'sessions': sessions,
        'members': members,
        'pending_requests': pending_requests,
        'has_pending_request': has_pending_request,
    }
    return render(request, 'halaqat/halaqa_detail.html', context)


@login_required
def edit_halaqa_view(request, pk):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية تعديل بيانات هذه الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    if request.method == 'POST':
        form = HalaqaForm(request.POST, instance=halaqa)
        if form.is_valid():
            form.save()
            messages.success(request, "تم حفظ تعديلات الحلقة بنجاح.")
            return redirect('halaqat:detail', pk=pk)
        else:
            messages.error(request, "يرجى تصحيح الأخطاء الموضحة.")
    else:
        form = HalaqaForm(instance=halaqa)

    return render(request, 'halaqat/edit_halaqa.html', {'form': form, 'halaqa': halaqa})


@login_required
def manage_members_view(request, pk):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية إدارة أعضاء هذه الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    add_form = AddMemberByPhoneForm()

    if request.method == 'POST' and 'add_member' in request.POST:
        add_form = AddMemberByPhoneForm(request.POST)
        if add_form.is_valid():
            phone = add_form.cleaned_data['phone'].strip()
            role = add_form.cleaned_data['role']

            target_user = User.objects.filter(phone=phone).first()
            if not target_user:
                messages.error(request, f"لم يتم العثور على مستخدم مسجل برقم الهاتف '{phone}'. يجب أن يسجل المستخدم حسابه في المنصة أولاً.")
            elif target_user.is_suspended:
                messages.error(request, "هذا الحساب معلق حالياً ولا يمكن إضافته للحلقة.")
            elif halaqa.members.filter(user=target_user).exists():
                messages.warning(request, f"المستخدم {target_user.display_name} عضو بالفعل في هذه الحلقة.")
            else:
                # Rule 8: Students can only join Halaqat matching their gender
                if role == HalaqaMember.ROLE_STUDENT and target_user.gender != halaqa.gender:
                    messages.error(
                        request,
                        f"تعذر إضافة الطالب: جنس المستخدم ({target_user.get_gender_display()}) لا يتطابق مع فئة الحلقة ({halaqa.get_gender_display()})."
                    )
                else:
                    member = HalaqaMember.objects.create(
                        halaqa=halaqa,
                        user=target_user,
                        role=role,
                        can_manage_sessions=add_form.cleaned_data['can_manage_sessions'],
                        can_record_attendance=add_form.cleaned_data['can_record_attendance'],
                        can_record_recitation=add_form.cleaned_data['can_record_recitation'],
                        can_manage_members=add_form.cleaned_data['can_manage_members']
                    )
                    notify_user(
                        recipient=target_user,
                        actor=request.user,
                        title=f"تمت إضافتك إلى حلقة {halaqa.name}",
                        message=f"أهلاً بك! لقد قام {request.user.display_name} بإضافتك إلى حلقة '{halaqa.name}' بدور ({member.get_role_display()}).",
                        link=f"/halaqat/{halaqa.id}/",
                        notification_type=Notification.TYPE_GENERAL
                    )
                    messages.success(request, f"تمت إضافة {target_user.display_name} بنجاح كـ {member.get_role_display()}.")
                    return redirect('halaqat:manage_members', pk=pk)

    members = halaqa.members.select_related('user').order_by('role', 'joined_at')
    pending_requests = halaqa.join_requests.filter(status=JoinRequest.STATUS_PENDING).select_related('user')

    context = {
        'halaqa': halaqa,
        'members': members,
        'add_form': add_form,
        'pending_requests': pending_requests,
    }
    return render(request, 'halaqat/manage_members.html', context)


@login_required
def update_member_role_view(request, pk, member_id):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية تعديل صلاحيات الأعضاء.")
        return redirect('halaqat:detail', pk=pk)

    member = get_object_or_404(HalaqaMember, pk=member_id, halaqa=halaqa)
    if member.role == HalaqaMember.ROLE_OWNER and member.user != request.user and not request.user.is_platform_admin:
        messages.error(request, "لا يمكن تعديل صلاحيات مالك الحلقة.")
        return redirect('halaqat:manage_members', pk=pk)

    if request.method == 'POST':
        form = UpdateMemberRoleForm(request.POST, instance=member)
        if form.is_valid():
            updated_member = form.save(commit=False)
            # Gender check if changing to student
            if updated_member.role == HalaqaMember.ROLE_STUDENT and member.user.gender != halaqa.gender:
                messages.error(request, "لا يمكن تحويل العضو إلى طالب لأن جنسه لا يطابق فئة الحلقة.")
            else:
                updated_member.save()
                messages.success(request, f"تم تحديث صلاحيات {member.user.display_name} بنجاح.")
                return redirect('halaqat:manage_members', pk=pk)
    else:
        form = UpdateMemberRoleForm(instance=member)

    return render(request, 'halaqat/update_member.html', {'form': form, 'halaqa': halaqa, 'member': member})


@login_required
def remove_member_view(request, pk, member_id):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية حذف أعضاء من الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    member = get_object_or_404(HalaqaMember, pk=member_id, halaqa=halaqa)
    if member.role == HalaqaMember.ROLE_OWNER:
        messages.error(request, "لا يمكن حذف مالك الحلقة.")
        return redirect('halaqat:manage_members', pk=pk)

    if request.method == 'POST':
        user_name = member.user.display_name
        member.delete()
        messages.success(request, f"تم إخراج {user_name} من الحلقة.")
        return redirect('halaqat:manage_members', pk=pk)

    return render(request, 'halaqat/confirm_remove_member.html', {'halaqa': halaqa, 'member': member})


@login_required
def request_join_halaqa_view(request, pk):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    user = request.user

    # Rule 6: Private halaqat can only be joined through teacher invitations
    if halaqa.visibility == Halaqa.VISIBILITY_PRIVATE:
        messages.error(request, "هذه الحلقة خاصة ويمكن الانضمام إليها بدعوة من المعلم فقط.")
        return redirect('halaqat:browse_public')

    # Rule 8: Students can only join Halaqat matching their gender
    if user.gender != halaqa.gender:
        messages.error(request, f"عذراً، هذه الحلقة مخصصة لفئة ({halaqa.get_gender_display()}) فقط.")
        return redirect('halaqat:browse_public')

    # Already member?
    if halaqa.members.filter(user=user).exists():
        messages.info(request, "أنت عضو بالفعل في هذه الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    # Check existing pending request
    existing_request = JoinRequest.objects.filter(halaqa=halaqa, user=user, status=JoinRequest.STATUS_PENDING).first()
    if existing_request:
        messages.info(request, "طلب انضمامك قيد المراجعة حالياً من قبل إدارة الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    if request.method == 'POST':
        JoinRequest.objects.create(halaqa=halaqa, user=user, status=JoinRequest.STATUS_PENDING)
        
        # Notify owner and teachers
        notify_user(
            recipient=halaqa.owner,
            actor=user,
            title="طلب انضمام جديد للحلقة",
            message=f"قام الطالب {user.display_name} بطلب الانضمام إلى حلقة '{halaqa.name}'.",
            link=f"/halaqat/{halaqa.id}/members/",
            notification_type=Notification.TYPE_JOIN_REQUEST
        )
        messages.success(request, "تم إرسال طلب انضمامك بنجاح! سيتم إشعارك فور مراجعته وقبوله.")
        return redirect('halaqat:detail', pk=pk)

    return render(request, 'halaqat/confirm_join_request.html', {'halaqa': halaqa})


@login_required
def handle_join_request_view(request, pk, req_id, action):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية البت في طلبات الانضمام.")
        return redirect('halaqat:detail', pk=pk)

    join_req = get_object_or_404(JoinRequest, pk=req_id, halaqa=halaqa)
    if join_req.status != JoinRequest.STATUS_PENDING:
        messages.info(request, "تم التعامل مع هذا الطلب مسبقاً.")
        return redirect('halaqat:manage_members', pk=pk)

    if action == 'approve':
        # Verify gender again
        if join_req.user.gender != halaqa.gender:
            messages.error(request, "لا يمكن قبول الطالب لعدم تطابق الجنس مع فئة الحلقة.")
            return redirect('halaqat:manage_members', pk=pk)

        # Create student member
        HalaqaMember.objects.get_or_create(
            halaqa=halaqa,
            user=join_req.user,
            defaults={'role': HalaqaMember.ROLE_STUDENT}
        )
        join_req.status = JoinRequest.STATUS_APPROVED
        join_req.reviewed_at = timezone.now()
        join_req.reviewed_by = request.user
        join_req.save()

        notify_user(
            recipient=join_req.user,
            actor=request.user,
            title=f"تم قبول انضمامك لحلقة {halaqa.name}",
            message=f"مبروك! تمت الموافقة على انضمامك إلى حلقة '{halaqa.name}'. يمكنك الآن متابعة الجلسات والتسميع.",
            link=f"/halaqat/{halaqa.id}/",
            notification_type=Notification.TYPE_REQUEST_STATUS
        )
        messages.success(request, f"تم قبول انضمام الطالب {join_req.user.display_name} بنجاح.")

    elif action == 'reject':
        join_req.status = JoinRequest.STATUS_REJECTED
        join_req.reviewed_at = timezone.now()
        join_req.reviewed_by = request.user
        join_req.save()

        notify_user(
            recipient=join_req.user,
            actor=request.user,
            title=f"تحديث بخصوص طلب انضمامك لحلقة {halaqa.name}",
            message=f"نعتذر، لم تتم الموافقة على طلب انضمامك إلى حلقة '{halaqa.name}'.",
            link=f"/halaqat/browse/",
            notification_type=Notification.TYPE_REQUEST_STATUS
        )
        messages.info(request, f"تم رفض طلب انضمام {join_req.user.display_name}.")

    return redirect('halaqat:manage_members', pk=pk)


from django.db import transaction
from attendance.models import Attendance
from recitations.models import Recitation
from halaqa_sessions.models import Session


@login_required
def student_progress_sheet_view(request, pk, student_id):
    """
    Displays the comprehensive follow-up sheet (جدول المتابعة القرآني) for a student in a specific Halaqa.
    Includes history of new memorization, near revision, far revision, performance ratings, and next assignments.
    Allows authorized teachers to log or update progress directly.
    """
    halaqa = get_object_or_404(Halaqa, pk=pk)
    student = get_object_or_404(User, pk=student_id)

    # Check permission
    is_self = (request.user.id == student.id)
    is_owner = halaqa.is_owner(request.user)
    is_admin = request.user.is_platform_admin
    can_record_rec = halaqa.can_record_recitation(request.user)
    can_record_att = halaqa.can_record_attendance(request.user)
    can_manage = is_owner or is_admin or can_record_rec or can_record_att

    if not (is_self or can_manage):
        messages.error(request, "ليست لديك صلاحية عرض جدول متابعة هذا الطالب.")
        return redirect('halaqat:detail', pk=pk)

    # Handle quick progress logging by teacher/assistant
    if request.method == 'POST' and can_manage:
        session_id = request.POST.get('session_id')
        session = get_object_or_404(Session, pk=session_id, halaqa=halaqa)
        
        att_status = request.POST.get('attendance_status')
        att_notes = request.POST.get('attendance_notes', '').strip()

        new_mem = request.POST.get('new_memorization', '').strip()
        near_rev = request.POST.get('near_revision', '').strip()
        far_rev = request.POST.get('far_revision', '').strip()
        rating = request.POST.get('rating')
        notes = request.POST.get('teacher_notes', '').strip()
        next_assign = request.POST.get('next_assignment', '').strip()

        with transaction.atomic():
            # 1. Update or create attendance
            if att_status:
                att_obj = Attendance.objects.filter(session=session, student=student).first()
                if att_obj:
                    att_obj.status = att_status
                    att_obj.notes = att_notes
                    att_obj.updated_by = request.user
                    att_obj.save()
                else:
                    Attendance.objects.create(
                        session=session,
                        student=student,
                        status=att_status,
                        notes=att_notes,
                        created_by=request.user
                    )

            # 2. Update or create recitation if rating is provided
            if rating and rating in [r[0] for r in Recitation.RATING_CHOICES]:
                rec_obj = Recitation.objects.filter(session=session, student=student).first()
                if rec_obj:
                    rec_obj.new_memorization = new_mem
                    rec_obj.near_revision = near_rev
                    rec_obj.far_revision = far_rev
                    rec_obj.rating = rating
                    rec_obj.teacher_notes = notes
                    rec_obj.next_assignment = next_assign
                    rec_obj.updated_by = request.user
                    rec_obj.save()
                else:
                    Recitation.objects.create(
                        session=session,
                        student=student,
                        new_memorization=new_mem,
                        near_revision=near_rev,
                        far_revision=far_rev,
                        rating=rating,
                        teacher_notes=notes,
                        next_assignment=next_assign,
                        created_by=request.user
                    )

        messages.success(request, f"تم حفظ وتحديث بيانات المتابعة والتسميع للطالب {student.display_name} بنجاح.")
        return redirect('halaqat:student_progress', pk=pk, student_id=student_id)

    # Fetch sessions in this halaqa
    sessions = halaqa.sessions.all().order_by('-date', '-start_time')
    
    # Fetch attendances and recitations
    attendances = Attendance.objects.filter(session__halaqa=halaqa, student=student).select_related('session')
    recitations = Recitation.objects.filter(session__halaqa=halaqa, student=student).select_related('session')

    att_map = {a.session_id: a for a in attendances}
    rec_map = {r.session_id: r for r in recitations}

    # Build progress rows
    progress_rows = []
    for s in sessions:
        att = att_map.get(s.id)
        rec = rec_map.get(s.id)
        progress_rows.append({
            'session': s,
            'attendance': att,
            'recitation': rec,
        })

    # Stats
    total_records = attendances.count()
    present_count = attendances.filter(status=Attendance.STATUS_PRESENT).count()
    absent_count = attendances.filter(status=Attendance.STATUS_ABSENT).count()
    late_count = attendances.filter(status=Attendance.STATUS_LATE).count()
    excused_count = attendances.filter(status=Attendance.STATUS_EXCUSED).count()

    ratings_counts = {
        'MUMTAZ': recitations.filter(rating=Recitation.RATING_MUMTAZ).count(),
        'JAYYID_JIDDAN': recitations.filter(rating=Recitation.RATING_JAYYID_JIDDAN).count(),
        'JAYYID': recitations.filter(rating=Recitation.RATING_JAYYID).count(),
        'MAQBOOL': recitations.filter(rating=Recitation.RATING_MAQBOOL).count(),
        'DAEEF': recitations.filter(rating=Recitation.RATING_DAEEF).count(),
    }

    # Latest assigned homework
    latest_rec = recitations.exclude(next_assignment='').order_by('-session__date').first()
    latest_assignment = latest_rec.next_assignment if latest_rec else None

    context = {
        'halaqa': halaqa,
        'student': student,
        'sessions': sessions,
        'progress_rows': progress_rows,
        'can_manage': can_manage,
        'is_self': is_self,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'ratings_counts': ratings_counts,
        'latest_assignment': latest_assignment,
        'rating_choices': Recitation.RATING_CHOICES,
    }
    return render(request, 'halaqat/student_progress.html', context)

@login_required
def schedule_create_view(request, pk):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية إضافة مواعيد لهذه الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    if request.method == 'POST':
        form = HalaqaScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.halaqa = halaqa
            schedule.save()
            messages.success(request, "تمت إضافة موعد الحلقة بنجاح.")
            return redirect('halaqat:detail', pk=pk)
        else:
            messages.error(request, "يرجى تصحيح الأخطاء في نموذج الموعد.")
    else:
        form = HalaqaScheduleForm()

    return render(request, 'halaqat/schedule_form.html', {'form': form, 'halaqa': halaqa, 'is_edit': False})


@login_required
def schedule_edit_view(request, pk, schedule_id):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية تعديل مواعيد هذه الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    schedule = get_object_or_404(HalaqaSchedule, pk=schedule_id, halaqa=halaqa)

    if request.method == 'POST':
        form = HalaqaScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل الموعد بنجاح.")
            return redirect('halaqat:detail', pk=pk)
        else:
            messages.error(request, "يرجى تصحيح الأخطاء في نموذج الموعد.")
    else:
        form = HalaqaScheduleForm(instance=schedule)

    return render(request, 'halaqat/schedule_form.html', {'form': form, 'halaqa': halaqa, 'is_edit': True})


@login_required
def schedule_delete_view(request, pk, schedule_id):
    halaqa = get_object_or_404(Halaqa, pk=pk)
    if not halaqa.can_manage_halaqa(request.user):
        messages.error(request, "ليست لديك صلاحية حذف مواعيد هذه الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    schedule = get_object_or_404(HalaqaSchedule, pk=schedule_id, halaqa=halaqa)

    if request.method == 'POST':
        schedule.delete()
        messages.success(request, "تم حذف موعد الحلقة.")
        return redirect('halaqat:detail', pk=pk)

    return render(request, 'halaqat/confirm_delete_schedule.html', {'halaqa': halaqa, 'schedule': schedule})

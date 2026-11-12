from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from accounts.models import User
from halaqat.models import Halaqa, HalaqaMember
from halaqa_sessions.models import Session
from attendance.models import Attendance
from recitations.models import Recitation


def is_platform_admin(user):
    return user.is_authenticated and (user.role == User.ROLE_ADMIN or user.is_superuser or user.is_staff)


@login_required
@user_passes_test(is_platform_admin, login_url='accounts:login')
def dashboard_overview_view(request):
    total_users = User.objects.count()
    total_teachers = User.objects.filter(role=User.ROLE_TEACHER).count()
    total_students = User.objects.filter(role=User.ROLE_STUDENT).count()
    total_suspended = User.objects.filter(is_suspended=True).count()

    total_halaqat = Halaqa.objects.count()
    total_sessions = Session.objects.count()
    completed_sessions = Session.objects.filter(status=Session.STATUS_COMPLETED).count()
    total_recitations = Recitation.objects.count()

    recent_users = User.objects.order_by('-date_joined')[:6]
    recent_halaqat = Halaqa.objects.select_related('owner').order_by('-created_at')[:6]

    context = {
        'total_users': total_users,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'total_suspended': total_suspended,
        'total_halaqat': total_halaqat,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'total_recitations': total_recitations,
        'recent_users': recent_users,
        'recent_halaqat': recent_halaqat,
    }
    return render(request, 'dashboard/overview.html', context)


@login_required
@user_passes_test(is_platform_admin, login_url='accounts:login')
def users_list_view(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    gender_filter = request.GET.get('gender', '')

    users = User.objects.all().order_by('-date_joined')

    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    if status_filter == 'suspended':
        users = users.filter(is_suspended=True)
    elif status_filter == 'active':
        users = users.filter(is_suspended=False)

    if gender_filter:
        users = users.filter(gender=gender_filter)

    context = {
        'users': users,
        'query': query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'gender_filter': gender_filter,
    }
    return render(request, 'dashboard/users_list.html', context)


@login_required
@user_passes_test(is_platform_admin, login_url='accounts:login')
def user_detail_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    # Halaqat memberships
    memberships = HalaqaMember.objects.filter(user=target_user).select_related('halaqa')
    owned_halaqat = Halaqa.objects.filter(owner=target_user)

    # Activity stats
    attendances_count = Attendance.objects.filter(student=target_user).count()
    recitations_count = Recitation.objects.filter(student=target_user).count()

    context = {
        'target_user': target_user,
        'memberships': memberships,
        'owned_halaqat': owned_halaqat,
        'attendances_count': attendances_count,
        'recitations_count': recitations_count,
    }
    return render(request, 'dashboard/user_detail.html', context)


@login_required
@user_passes_test(is_platform_admin, login_url='accounts:login')
def toggle_user_suspend_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, "لا يمكنك تعليق حسابك الخاص.")
        return redirect('dashboard:user_detail', pk=pk)

    if request.method == 'POST':
        target_user.is_suspended = not target_user.is_suspended
        target_user.save(update_fields=['is_suspended'])
        action_word = "تعليق" if target_user.is_suspended else "إلغاء تعليق وتنشيط"
        messages.success(request, f"تم {action_word} حساب {target_user.display_name} بنجاح.")
        return redirect('dashboard:user_detail', pk=pk)

    return redirect('dashboard:user_detail', pk=pk)


@login_required
@user_passes_test(is_platform_admin, login_url='accounts:login')
def halaqat_list_view(request):
    query = request.GET.get('q', '').strip()
    gender_filter = request.GET.get('gender', '')
    visibility_filter = request.GET.get('visibility', '')

    halaqat = Halaqa.objects.select_related('owner').annotate(
        members_count=Count('members', distinct=True),
        sessions_count=Count('sessions', distinct=True)
    ).order_by('-created_at')

    if query:
        halaqat = halaqat.filter(
            Q(name__icontains=query) |
            Q(owner__first_name__icontains=query) |
            Q(owner__phone__icontains=query)
        )

    if gender_filter:
        halaqat = halaqat.filter(gender=gender_filter)

    if visibility_filter:
        halaqat = halaqat.filter(visibility=visibility_filter)

    context = {
        'halaqat': halaqat,
        'query': query,
        'gender_filter': gender_filter,
        'visibility_filter': visibility_filter,
    }
    return render(request, 'dashboard/halaqat_list.html', context)

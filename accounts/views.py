from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from .forms import UserRegistrationForm, LoginForm, UserProfileForm
from .models import User
from attendance.models import Attendance
from recitations.models import Recitation


def register_view(request):
    if request.user.is_authenticated:
        return redirect('halaqat:my_halaqat')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"أهلاً بك يا {user.display_name}! تم إنشاء حسابك بنجاح. يمكنك الآن تسجيل الدخول.")
            return redirect('accounts:login')
        else:
            messages.error(request, "يرجى تصحيح الأخطاء الموضحة أدناه.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('halaqat:my_halaqat')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_field = form.cleaned_data['login_field']
            password = form.cleaned_data['password']

            # Check if user exists and is suspended before failing silently
            matched_user = User.objects.filter(
                Q(username__iexact=login_field) |
                Q(email__iexact=login_field) |
                Q(phone=login_field)
            ).first()

            if matched_user and matched_user.is_suspended:
                messages.error(request, "عذراً، هذا الحساب معلق حالياً من قبل الإدارة. يرجى التواصل مع الدعم الفني.")
                return render(request, 'accounts/login.html', {'form': form})

            user = authenticate(request, username=login_field, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"مرحباً بك مجدداً، {user.display_name}!")
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('halaqat:my_halaqat')
            else:
                messages.error(request, "بيانات الدخول غير صحيحة. يرجى التأكد من اسم المستخدم/الهاتف وكلمة المرور.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "تم تسجيل خروجك بنجاح.")
        return redirect('accounts:login')
    return redirect('halaqat:my_halaqat')


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات ملفك الشخصي بنجاح.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "يرجى تصحيح الأخطاء الموضحة أدناه.")
    else:
        form = UserProfileForm(instance=user)

    return render(request, 'accounts/profile.html', {'form': form, 'user_obj': user})


@login_required
def my_progress_view(request):
    """
    Shows student's attendance history and recitation progress across all halaqat.
    """
    user = request.user

    # Fetch active attendances
    attendances = Attendance.objects.filter(student=user, session__is_deleted=False).select_related('session', 'session__halaqa').order_by('-session__date')
    
    # Fetch active recitations
    recitations = Recitation.objects.filter(student=user, session__is_deleted=False).select_related('session', 'session__halaqa').order_by('-session__date')

    # Calculate stats
    total_sessions_recorded = attendances.count()
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

    context = {
        'attendances': attendances,
        'recitations': recitations,
        'total_sessions_recorded': total_sessions_recorded,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'ratings_counts': ratings_counts,
    }
    return render(request, 'accounts/my_progress.html', context)

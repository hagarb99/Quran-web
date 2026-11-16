from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import get_user_subscription_status
from .models import Subscription, StudentSubscriptionProfile


@login_required
def status_notice_view(request):
    """
    Displays current subscription status, validity, and manual payment contact details.
    """
    user = request.user
    status = get_user_subscription_status(user)

    teacher_subscription = None
    student_profile = None

    if user.role == user.ROLE_TEACHER:
        teacher_subscription = Subscription.objects.filter(owner=user).order_by('-created_at').first()
    elif user.role == user.ROLE_STUDENT:
        student_profile = StudentSubscriptionProfile.objects.filter(student=user).first()
        if student_profile and student_profile.teacher:
            teacher_subscription = Subscription.objects.filter(owner=student_profile.teacher).order_by('-created_at').first()

    context = {
        'status': status,
        'teacher_subscription': teacher_subscription,
        'student_profile': student_profile,
    }
    return render(request, 'subscriptions/status_notice.html', context)

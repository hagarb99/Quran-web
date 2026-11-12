from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notifications_list_view(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
    return render(request, 'notifications/notifications_list.html', {'notifications': notifications})


@login_required
def notification_read_and_redirect(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])

    if notif.link:
        return redirect(notif.link)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "تم تحديد جميع الإشعارات كمقروءة.")
    return redirect('notifications:list')

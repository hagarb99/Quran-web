from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from .services import has_active_access, get_user_subscription_status


def subscription_required(view_func):
    """
    Decorator for views that require an active subscription (ACTIVE or FREE_TRIAL).
    Allows Platform Admins full access.
    Restricted users (PENDING, PAUSED, CLOSED, EXPIRED) are blocked server-side.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if request.user.is_platform_admin:
            return view_func(request, *args, **kwargs)

        if not has_active_access(request.user):
            status = get_user_subscription_status(request.user)
            status_labels = {
                'PENDING': 'قيد الانتظار أو بانتظار التجديد',
                'PAUSED': 'موقوف مؤقتاً',
                'CLOSED': 'مغلق',
                'EXPIRED': 'منتهي الصلاحية',
            }
            status_text = status_labels.get(status, 'غير نشط')

            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.endswith('/api/'):
                return JsonResponse({
                    'error': 'subscription_required',
                    'status': status,
                    'message': f'عذراً، حسابك بحالة ({status_text}) ويتطلب اشتراكاً نشطاً للمتابعة.'
                }, status=403)

            messages.warning(
                request,
                f"عذراً، يتطلب الوصول لهذه الخاصية اشتراكاً نشطاً. حالة اشتراكك حالياً: ({status_text}). يرجى التواصل مع إدارة المنصة للتفعيل أو التجديد."
            )
            return redirect('subscriptions:status_notice')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


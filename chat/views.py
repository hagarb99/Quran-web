from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q
from django.utils import timezone
from .models import Conversation, Message
from halaqat.models import Halaqa, HalaqaMember
from accounts.models import User
from notifications.models import notify_user, Notification


@login_required
def conversations_list_view(request):
    user = request.user

    # Halaqat group conversations where user is member or owner
    user_halaqa_ids = HalaqaMember.objects.filter(user=user).values_list('halaqa_id', flat=True)
    owned_halaqa_ids = Halaqa.objects.filter(owner=user).values_list('id', flat=True)
    all_halaqa_ids = set(user_halaqa_ids).union(set(owned_halaqa_ids))

    group_chats = Conversation.objects.filter(
        chat_type=Conversation.TYPE_GROUP,
        halaqa_id__in=all_halaqa_ids
    ).select_related('halaqa').prefetch_related('messages')

    # Direct chats where user is participant1 or participant2
    direct_chats = Conversation.objects.filter(
        chat_type=Conversation.TYPE_DIRECT
    ).filter(
        Q(participant1=user) | Q(participant2=user)
    ).select_related('participant1', 'participant2').prefetch_related('messages')

    context = {
        'group_chats': group_chats,
        'direct_chats': direct_chats,
    }
    return render(request, 'chat/conversations_list.html', context)


@login_required
def start_direct_chat_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        return redirect('chat:conversations_list')

    # Find existing conversation between the two users
    conv = Conversation.objects.filter(
        chat_type=Conversation.TYPE_DIRECT
    ).filter(
        (Q(participant1=request.user) & Q(participant2=target_user)) |
        (Q(participant1=target_user) & Q(participant2=request.user))
    ).first()

    if not conv:
        conv = Conversation.objects.create(
            chat_type=Conversation.TYPE_DIRECT,
            participant1=request.user,
            participant2=target_user
        )

    return redirect('chat:conversation_detail', pk=conv.pk)


@login_required
@ensure_csrf_cookie
def conversation_detail_view(request, pk):
    conv = get_object_or_404(Conversation.objects.select_related('halaqa', 'participant1', 'participant2'), pk=pk)
    if not conv.can_access(request.user):
        return HttpResponseForbidden("لا تملك صلاحية الوصول إلى هذه المحادثة.")

    # Fetch initial latest 25 messages ordered ascending for display
    latest_messages = list(conv.messages.select_related('sender').order_by('-created_at')[:25])
    latest_messages.reverse()

    oldest_id = latest_messages[0].id if latest_messages else 0
    latest_id = latest_messages[-1].id if latest_messages else 0

    title = conv.get_title_for_user(request.user)

    context = {
        'conversation': conv,
        'title': title,
        'initial_messages': latest_messages,
        'oldest_id': oldest_id,
        'latest_id': latest_id,
    }
    return render(request, 'chat/conversation_detail.html', context)


@login_required
@require_POST
def send_message_api(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.can_access(request.user):
        return JsonResponse({'error': 'غير مصرح لك بالإرسال في هذه المحادثة.'}, status=403)

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'لا يمكن إرسال رسالة فارغة.'}, status=400)

    msg = Message.objects.create(
        conversation=conv,
        sender=request.user,
        content=content
    )
    conv.updated_at = timezone.now()
    conv.save(update_fields=['updated_at'])

    # Send in-app notification to other participants
    if conv.chat_type == Conversation.TYPE_DIRECT:
        other_user = conv.get_other_participant(request.user)
        if other_user:
            notify_user(
                recipient=other_user,
                actor=request.user,
                title=f"رسالة جديدة من {request.user.display_name}",
                message=content[:80],
                link=f"/chat/{conv.id}/",
                notification_type=Notification.TYPE_CHAT_MESSAGE
            )
    elif conv.chat_type == Conversation.TYPE_GROUP and conv.halaqa:
        for member in conv.halaqa.members.select_related('user').all():
            if member.user != request.user:
                notify_user(
                    recipient=member.user,
                    actor=request.user,
                    title=f"رسالة جديدة في حلقة {conv.halaqa.name}",
                    message=f"{request.user.display_name}: {content[:70]}",
                    link=f"/chat/{conv.id}/",
                    notification_type=Notification.TYPE_CHAT_MESSAGE
                )

    return JsonResponse({
        'status': 'success',
        'message': {
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.display_name,
            'content': msg.content,
            'created_at': msg.created_at.strftime('%H:%M'),
            'is_me': True,
        }
    })


@login_required
@require_GET
def poll_messages_api(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.can_access(request.user):
        return JsonResponse({'error': 'غير مصرح.'}, status=403)

    try:
        after_id = int(request.GET.get('after', 0))
    except ValueError:
        after_id = 0

    new_messages = conv.messages.filter(id__gt=after_id).select_related('sender').order_by('created_at')

    data = [
        {
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.display_name,
            'content': m.content,
            'created_at': m.created_at.strftime('%H:%M'),
            'is_me': (m.sender_id == request.user.id),
        }
        for m in new_messages
    ]
    return JsonResponse({'messages': data})


@login_required
@require_GET
def history_messages_api(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.can_access(request.user):
        return JsonResponse({'error': 'غير مصرح.'}, status=403)

    try:
        before_id = int(request.GET.get('before', 0))
    except ValueError:
        return JsonResponse({'messages': []})

    older_messages = list(
        conv.messages.filter(id__lt=before_id).select_related('sender').order_by('-created_at')[:25]
    )
    older_messages.reverse()

    data = [
        {
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.display_name,
            'content': m.content,
            'created_at': m.created_at.strftime('%H:%M'),
            'is_me': (m.sender_id == request.user.id),
        }
        for m in older_messages
    ]
    return JsonResponse({'messages': data})

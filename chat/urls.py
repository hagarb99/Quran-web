from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.conversations_list_view, name='conversations_list'),
    path('start/<int:user_id>/', views.start_direct_chat_view, name='start_direct'),
    path('<int:pk>/', views.conversation_detail_view, name='conversation_detail'),
    path('<int:pk>/send/', views.send_message_api, name='send_message'),
    path('<int:pk>/poll/', views.poll_messages_api, name='poll_messages'),
    path('<int:pk>/history/', views.history_messages_api, name='history_messages'),
]


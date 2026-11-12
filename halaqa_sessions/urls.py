from django.urls import path
from . import views

app_name = 'halaqa_sessions'

urlpatterns = [
    path('halaqa/<int:halaqa_id>/create/', views.session_create_view, name='create'),
    path('<int:pk>/', views.session_detail_view, name='detail'),
    path('<int:pk>/edit/', views.session_edit_view, name='edit'),
    path('<int:pk>/action/<str:action>/', views.session_action_view, name='action'),
    path('<int:pk>/delete/', views.session_delete_view, name='delete'),
]


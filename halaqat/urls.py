from django.urls import path
from . import views

app_name = 'halaqat'

urlpatterns = [
    path('', views.my_halaqat_view, name='my_halaqat'),
    path('browse/', views.browse_public_view, name='browse_public'),
    path('create/', views.create_halaqa_view, name='create'),
    path('<int:pk>/', views.halaqa_detail_view, name='detail'),
    path('<int:pk>/edit/', views.edit_halaqa_view, name='edit'),
    path('<int:pk>/join/', views.request_join_halaqa_view, name='request_join'),
    path('<int:pk>/members/', views.manage_members_view, name='manage_members'),
    path('<int:pk>/members/<int:member_id>/update/', views.update_member_role_view, name='update_member_role'),
    path('<int:pk>/members/<int:member_id>/remove/', views.remove_member_view, name='remove_member'),
    path('<int:pk>/students/<int:student_id>/progress/', views.student_progress_sheet_view, name='student_progress'),
    path('<int:pk>/requests/<int:req_id>/<str:action>/', views.handle_join_request_view, name='handle_join_request'),
    # Schedules
    path('<int:pk>/schedules/create/', views.schedule_create_view, name='schedule_create'),
    path('<int:pk>/schedules/<int:schedule_id>/edit/', views.schedule_edit_view, name='schedule_edit'),
    path('<int:pk>/schedules/<int:schedule_id>/delete/', views.schedule_delete_view, name='schedule_delete'),
]


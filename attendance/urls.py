from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('session/<int:session_id>/student/<int:student_id>/', views.record_attendance_view, name='record'),
    path('<int:pk>/delete/', views.delete_attendance_view, name='delete'),
]


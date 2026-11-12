from django.urls import path
from . import views

app_name = 'recitations'

urlpatterns = [
    path('session/<int:session_id>/student/<int:student_id>/', views.record_recitation_view, name='record'),
    path('<int:pk>/delete/', views.delete_recitation_view, name='delete'),
]


from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_overview_view, name='overview'),
    path('users/', views.users_list_view, name='users_list'),
    path('users/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('users/<int:pk>/toggle-suspend/', views.toggle_user_suspend_view, name='toggle_user_suspend'),
    path('halaqat/', views.halaqat_list_view, name='halaqat_list'),
]


from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('status/', views.status_notice_view, name='status_notice'),
]


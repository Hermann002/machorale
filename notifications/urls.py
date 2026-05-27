from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('a/<slug:slug>/notifications/api/', views.list_notifications,
         name='list'),
    path('a/<slug:slug>/notifications/api/mark-read/', views.mark_all_read,
         name='mark_read'),
]

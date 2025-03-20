from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_log_file, name='upload_log_file'),
    path('dashboard/<int:log_file_id>/', views.dashboard, name='dashboard'),
    path('log-entry/<int:entry_id>/', views.log_entry_detail, name='log_entry_detail'),
    path('delete/<int:log_file_id>/', views.delete_log_file, name='delete_log_file'),
    path('download/<int:log_file_id>/', views.download_excel, name='download_excel'),
]
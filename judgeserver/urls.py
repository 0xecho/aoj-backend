from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('list/', views.judgeserver_list, name='judgeserver_list'),
    path('add/', views.add_judgeserver, name='add_judgeserver'),
    path('edit/<int:judgeserver_id>/', views.edit_judgeserver, name='edit_judgeserver'),
    path('dump/<int:judgeserver_id>/', views.dump_judgeserver, name='dump_judgeserver'),
    path('delete/<int:judgeserver_id>/', views.delete_judgeserver, name='delete_judgeserver'),

    path('delete-done/<int:judgeserver_id>/', views.delete_judgeserver_done, name='delete_judgeserver_done'),
  

   ]

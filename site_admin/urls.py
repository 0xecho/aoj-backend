from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('problem/', views.site_view_problem, name='site_view_problem'),
    path('user/', views.site_view_user, name='site_view_user'),
    path('user/edit/<int:user_id>/', views.edit_user, name='site_edit_user'),
    path('user/delete/<int:user_id>/', views.delete_user, name='site_delete_user'),
    path('user/delete-done/<int:user_id>/', views.delete_user_done, name='site_delete_user_done'),
    path('user_register/', views.user_register, name='site_user_register'),
    path('user_register_csv/', views.user_register_csv, name='site_user_register_csv'),
    path('generate-password/<str:role_type>/', views.generate_user_password, name='site_generate_user_password'),
    path('generate-password-done/<str:role_id>/', views.generate_password_done, name='site_generate_password_done'),
    path('contest/', views.site_contest_list, name='site_contest_list'),
    path('contest/detail/<contest_id>/', views.site_contest_detail, name='site_contest_detail'),
    path('delete-contest/<int:contest_id>/', views.site_delete_contest, name='site_delete_contest'),
    path('delete-contest-done/<int:contest_id>/', views.site_delete_contest_done, name='site_delete_contest_done'),
    path('rejudge/filter/', views.site_rejudge_submission_filter, name='site_rejudge_submission_filter'),
    path('single-rejudge/<int:submit_id>/', views.site_single_rejudge, name='site_single_rejudge'),
    path('multi-rejudge/<int:problem_id>/<int:contest_id>/<int:user_id>/', views.site_multi_rejudge, name='site_multi_rejudge'),
    path('rejudge/contest-select/', views.site_rejudge_contest_select, name='site_rejudge_contest_select'),
    path('rejudge/submission-list/<int:contest_id>/', views.site_rejudge_submission_list, name='site_rejudge_submission_list'),
    path('rejudge/process/', views.site_ajax_rejudge, name='site_ajax_rejudge'),
    ]

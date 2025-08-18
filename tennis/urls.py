from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),

    # Аутентификация
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Процесс бронирования
    path('booking/step1/', views.booking_step1, name='booking_step1'),
    path('booking/step2/', views.booking_step2, name='booking_step2'),
    path('booking/step3/', views.booking_step3, name='booking_step3'),
    path('booking/step4/', views.booking_step4, name='booking_step4'),
    path('booking/success/<int:booking_id>/', views.booking_success, name='booking_success'),

    # Управление бронированиями
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),

    # AJAX endpoints
    path('ajax/courts/', views.get_courts_ajax, name='get_courts_ajax'),
]
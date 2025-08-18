from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, time
from .models import TennisCenter, TennisCourt, Booking, BookingSession
from .forms import BookingStep2Form, BookingStep3Form, BookingStep4Form
import json


def home(request):
    """Главная страница"""
    tennis_centers = TennisCenter.objects.all()
    return render(request, 'tennis/home.html', {'tennis_centers': tennis_centers})


def register_view(request):
    """Регистрация пользователя"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан для {username}!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """Авторизация пользователя"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('booking_step1')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@login_required
def profile_view(request):
    """Личный кабинет пользователя"""
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'tennis/profile.html', {'bookings': bookings})


def get_or_create_booking_session(request):
    """Получение или создание сессии бронирования"""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    session, created = BookingSession.objects.get_or_create(
        session_key=session_key,
        defaults={'user': request.user if request.user.is_authenticated else None}
    )
    return session


@login_required
def booking_step1(request):
    """Шаг 1 - Выбор теннисного центра"""
    if request.method == 'POST':
        center_id = request.POST.get('tennis_center')
        if center_id:
            session = get_or_create_booking_session(request)
            session.tennis_center_id = center_id
            session.save()
            return redirect('booking_step2')
        else:
            messages.error(request, 'Пожалуйста, выберите теннисный центр')

    tennis_centers = TennisCenter.objects.all()
    return render(request, 'tennis/booking_step1.html', {'tennis_centers': tennis_centers})


@login_required
def booking_step2(request):
    """Шаг 2 - Выбор даты и времени"""
    session = get_or_create_booking_session(request)

    if not session.tennis_center_id:
        messages.error(request, 'Сначала выберите теннисный центр')
        return redirect('booking_step1')

    tennis_center = get_object_or_404(TennisCenter, pk=session.tennis_center_id)
    courts = TennisCourt.objects.filter(tennis_center=tennis_center)

    if request.method == 'POST':
        form = BookingStep2Form(request.POST, tennis_center=tennis_center)
        if form.is_valid():
            session.date = form.cleaned_data['date']
            session.start_time = form.cleaned_data['start_time']
            session.duration_hours = form.cleaned_data['duration_hours']
            session.court_id = form.cleaned_data['court'].id if form.cleaned_data['court'] else None
            session.save()
            return redirect('booking_step3')
    else:
        form = BookingStep2Form(tennis_center=tennis_center)

    return render(request, 'tennis/booking_step2.html', {
        'form': form,
        'tennis_center': tennis_center,
        'courts': courts
    })


@login_required
def booking_step3(request):
    """Шаг 3 - Дополнительные услуги"""
    session = get_or_create_booking_session(request)

    if not session.tennis_center_id or not session.date:
        messages.error(request, 'Пожалуйста, пройдите предыдущие шаги')
        return redirect('booking_step1')

    if request.method == 'POST':
        form = BookingStep3Form(request.POST)
        if form.is_valid():
            session.trainer_service = form.cleaned_data['trainer_service']
            session.racket_rental = form.cleaned_data['racket_rental']
            session.balls_rental = form.cleaned_data['balls_rental']
            session.save()
            return redirect('booking_step4')
    else:
        form = BookingStep3Form()

    return render(request, 'tennis/booking_step3.html', {'form': form})


@login_required
def booking_step4(request):
    """Шаг 4 - Подтверждение заявки"""
    session = get_or_create_booking_session(request)

    if not all([session.tennis_center_id, session.date, session.start_time]):
        messages.error(request, 'Пожалуйста, пройдите все предыдущие шаги')
        return redirect('booking_step1')

    tennis_center = get_object_or_404(TennisCenter, pk=session.tennis_center_id)
    court = None
    if session.court_id:
        court = get_object_or_404(TennisCourt, pk=session.court_id)
    else:
        # Если корт не выбран, берем первый доступный
        available_courts = get_available_courts(
            tennis_center, session.date, session.start_time, session.duration_hours
        )
        if available_courts:
            court = available_courts[0]
        else:
            messages.error(request, 'Нет доступных кортов на выбранное время')
            return redirect('booking_step2')

    # Расчет стоимости
    total_price = calculate_booking_price(court, session)

    if request.method == 'POST':
        form = BookingStep4Form(request.POST)
        if form.is_valid():
            # Создание бронирования
            booking = Booking.objects.create(
                tennis_center=tennis_center,
                court=court,
                user=request.user,
                date=session.date,
                start_time=session.start_time,
                duration_hours=session.duration_hours,
                trainer_service=session.trainer_service,
                racket_rental=session.racket_rental,
                balls_rental=session.balls_rental,
                total_price=total_price,
                full_name=form.cleaned_data['full_name'],
                phone=form.cleaned_data['phone'],
                email=form.cleaned_data['email'],
            )

            # Отправка email подтверждения
            send_booking_confirmation_email(booking)

            # Очистка сессии
            session.delete()

            messages.success(request, 'Бронирование успешно создано!')
            return redirect('booking_success', booking_id=booking.id)
    else:
        # Предзаполнение формы данными пользователя
        initial_data = {
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email,
        }
        form = BookingStep4Form(initial=initial_data)

    context = {
        'form': form,
        'tennis_center': tennis_center,
        'court': court,
        'session': session,
        'total_price': total_price,
    }

    return render(request, 'tennis/booking_step4.html', context)


@login_required
def booking_success(request, booking_id):
    """Страница успешного бронирования"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'tennis/booking_success.html', {'booking': booking})


@login_required
def cancel_booking(request, booking_id):
    """Отмена бронирования"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.can_be_cancelled():
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Бронирование успешно отменено')
    else:
        messages.error(request, 'Это бронирование нельзя отменить')

    return redirect('profile')


def get_available_courts(tennis_center, date, start_time, duration_hours):
    """Получение доступных кортов на указанное время"""
    end_time = (datetime.combine(date, start_time) + timedelta(hours=duration_hours)).time()

    # Находим все занятые корты на это время
    occupied_courts = Booking.objects.filter(
        tennis_center=tennis_center,
        date=date,
        status__in=['pending', 'paid']
    ).filter(
        Q(start_time__lt=end_time) &
        Q(start_time__gte=start_time) |
        Q(start_time__lte=start_time) &
        Q(start_time__gt=start_time)  # Упрощенная логика, можно улучшить
    ).values_list('court_id', flat=True)

    # Возвращаем свободные корты
    available_courts = TennisCourt.objects.filter(
        tennis_center=tennis_center
    ).exclude(id__in=occupied_courts)

    return available_courts


def calculate_booking_price(court, session):
    """Расчет стоимости бронирования"""
    base_price = court.price_per_hour * session.duration_hours

    # Дополнительные услуги
    trainer_price = 10000 if session.trainer_service else 0
    racket_price = session.racket_rental * 2000
    balls_price = 1000 if session.balls_rental else 0

    return base_price + trainer_price + racket_price + balls_price


def send_booking_confirmation_email(booking):
    """Отправка email подтверждения бронирования"""
    subject = f'Подтверждение бронирования - {booking.tennis_center.name}'
    message = f"""
    Здравствуйте, {booking.full_name}!

    Ваше бронирование успешно создано:

    Теннисный центр: {booking.tennis_center.name}
    Корт: {booking.court}
    Дата: {booking.date}
    Время: {booking.start_time}
    Продолжительность: {booking.duration_hours} час(а/ов)
    Общая стоимость: {booking.total_price} ₸

    Статус: {booking.get_status_display()}

    Спасибо за выбор нашего сервиса!
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Ошибка отправки email: {e}")


# AJAX views for dynamic content
def get_courts_ajax(request):
    """AJAX получение кортов для выбранного центра"""
    center_id = request.GET.get('center_id')
    if center_id:
        courts = TennisCourt.objects.filter(tennis_center_id=center_id)
        data = [{
            'id': court.id,
            'number': court.court_number,
            'price': float(court.price_per_hour),
            'surface': court.get_surface_type_display(),
            'indoor': court.indoor
        } for court in courts]
        return JsonResponse({'courts': data})
    return JsonResponse({'courts': []})
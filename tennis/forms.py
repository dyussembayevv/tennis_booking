from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime, date, time
from .models import TennisCenter, TennisCourt, Booking


class BookingStep2Form(forms.Form):
    """Форма для шага 2 - выбор даты и времени"""
    date = forms.DateField(
        label="Дата бронирования",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': date.today().strftime('%Y-%m-%d')
        })
    )

    start_time = forms.TimeField(
        label="Время начала",
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
            'step': '3600'  # Шаг в 1 час
        })
    )

    duration_hours = forms.ChoiceField(
        label="Продолжительность",
        choices=[(1, '1 час'), (2, '2 часа'), (3, '3 часа')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    court = forms.ModelChoiceField(
        label="Корт (опционально)",
        queryset=TennisCourt.objects.none(),
        required=False,
        empty_label="Любой доступный корт",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        self.tennis_center = kwargs.pop('tennis_center', None)
        super().__init__(*args, **kwargs)

        if self.tennis_center:
            self.fields['court'].queryset = TennisCourt.objects.filter(
                tennis_center=self.tennis_center
            )

    def clean_date(self):
        booking_date = self.cleaned_data['date']
        if booking_date < date.today():
            raise ValidationError("Нельзя бронировать на прошедшую дату")
        return booking_date

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']

        # Проверяем, что время в рамках работы центра
        if self.tennis_center:
            if start_time < self.tennis_center.opening_time:
                raise ValidationError(f"Центр открывается в {self.tennis_center.opening_time}")

            # Проверяем, что бронирование закончится до закрытия
            duration = int(self.data.get('duration_hours', 1))
            end_datetime = datetime.combine(date.today(), start_time)
            end_datetime = end_datetime.replace(hour=end_datetime.hour + duration)
            end_time = end_datetime.time()

            if end_time > self.tennis_center.closing_time:
                raise ValidationError(f"Бронирование должно закончиться до {self.tennis_center.closing_time}")

        return start_time

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        duration_hours = int(cleaned_data.get('duration_hours', 1))
        court = cleaned_data.get('court')

        if booking_date and start_time and self.tennis_center:
            # Проверяем доступность выбранного корта
            if court:
                if self.is_court_occupied(court, booking_date, start_time, duration_hours):
                    raise ValidationError("Выбранный корт занят на это время")
            else:
                # Проверяем, есть ли хотя бы один свободный корт
                available_courts = self.get_available_courts(booking_date, start_time, duration_hours)
                if not available_courts:
                    raise ValidationError("Нет свободных кортов на выбранное время")

        return cleaned_data

    def is_court_occupied(self, court, booking_date, start_time, duration_hours):
        """Проверка, занят ли корт на указанное время"""
        end_datetime = datetime.combine(booking_date, start_time)
        end_datetime = end_datetime.replace(hour=end_datetime.hour + duration_hours)
        end_time = end_datetime.time()

        overlapping_bookings = Booking.objects.filter(
            court=court,
            date=booking_date,
            status__in=['pending', 'paid']
        ).filter(
            start_time__lt=end_time,
            start_time__gte=start_time
        )

        return overlapping_bookings.exists()

    def get_available_courts(self, booking_date, start_time, duration_hours):
        """Получение списка свободных кортов"""
        all_courts = TennisCourt.objects.filter(tennis_center=self.tennis_center)
        available_courts = []

        for court in all_courts:
            if not self.is_court_occupied(court, booking_date, start_time, duration_hours):
                available_courts.append(court)

        return available_courts


class BookingStep3Form(forms.Form):
    """Форма для шага 3 - дополнительные услуги"""
    trainer_service = forms.BooleanField(
        label="Услуги тренера (+10000₸)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    racket_rental = forms.IntegerField(
        label="Количество ракеток (по 2000₸ за штуку)",
        min_value=0,
        max_value=4,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '4'
        })
    )

    balls_rental = forms.BooleanField(
        label="Аренда мячей (+1000₸)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BookingStep4Form(forms.Form):
    """Форма для шага 4 - подтверждение заявки"""
    full_name = forms.CharField(
        label="Полное имя",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше полное имя'
        })
    )

    phone = forms.CharField(
        label="Номер телефона",
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (777) 123-45-67'
        })
    )

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        # Простая валидация номера телефона
        if not phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '').isdigit():
            raise ValidationError("Введите корректный номер телефона")
        return phone


class CancelBookingForm(forms.Form):
    """Форма для отмены бронирования"""
    confirm = forms.BooleanField(
        label="Я подтверждаю отмену бронирования",
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
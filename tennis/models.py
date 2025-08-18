from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class TennisCenter(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    address = models.TextField(verbose_name="Адрес")
    phone_number = models.CharField(max_length=20, verbose_name="Номер телефона")
    email = models.EmailField(verbose_name="Email")
    number_of_courts = models.PositiveIntegerField(verbose_name="Количество кортов")
    opening_time = models.TimeField(verbose_name="Время открытия")
    closing_time = models.TimeField(verbose_name="Время закрытия")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Теннисный центр"
        verbose_name_plural = "Теннисные центры"

    def __str__(self):
        return self.name


class TennisCourt(models.Model):
    SURFACE_CHOICES = [
        ('clay', 'Грунт'),
        ('hard', 'Хард'),
        ('grass', 'Трава'),
    ]

    tennis_center = models.ForeignKey(
        TennisCenter,
        on_delete=models.CASCADE,
        related_name='courts',
        verbose_name="Теннисный центр"
    )
    court_number = models.PositiveIntegerField(verbose_name="Номер корта")
    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена за час"
    )
    surface_type = models.CharField(
        max_length=10,
        choices=SURFACE_CHOICES,
        verbose_name="Тип покрытия"
    )
    indoor = models.BooleanField(default=False, verbose_name="Крытый корт")

    class Meta:
        verbose_name = "Теннисный корт"
        verbose_name_plural = "Теннисные корты"
        unique_together = ['tennis_center', 'court_number']

    def __str__(self):
        return f"{self.tennis_center.name} - Корт {self.court_number}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('paid', 'Оплачено'),
        ('cancelled', 'Отменено'),
    ]

    tennis_center = models.ForeignKey(
        TennisCenter,
        on_delete=models.CASCADE,
        verbose_name="Теннисный центр"
    )
    court = models.ForeignKey(
        TennisCourt,
        on_delete=models.CASCADE,
        verbose_name="Корт"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    date = models.DateField(verbose_name="Дата")
    start_time = models.TimeField(verbose_name="Время начала")
    duration_hours = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        verbose_name="Продолжительность (часы)"
    )
    trainer_service = models.BooleanField(default=False, verbose_name="Услуги тренера")
    racket_rental = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(4)],
        verbose_name="Аренда ракеток"
    )
    balls_rental = models.BooleanField(default=False, verbose_name="Аренда мячей")
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Общая стоимость"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )

    # Контактная информация пользователя
    full_name = models.CharField(max_length=200, verbose_name="Полное имя")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(verbose_name="Email")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.date} {self.start_time}"

    def calculate_total_price(self):
        """Расчет общей стоимости бронирования"""
        base_price = self.court.price_per_hour * self.duration_hours

        # Дополнительные услуги (примерные цены)
        trainer_price = Decimal('10000') if self.trainer_service else Decimal('0')
        racket_price = self.racket_rental * Decimal('2000')
        balls_price = Decimal('1000') if self.balls_rental else Decimal('0')

        return base_price + trainer_price + racket_price + balls_price

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.calculate_total_price()
        super().save(*args, **kwargs)

    def can_be_cancelled(self):
        """Проверка, можно ли отменить бронирование"""
        return self.status == 'pending'


class BookingSession(models.Model):
    """Модель для хранения данных между шагами бронирования"""
    session_key = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    # Шаг 1 - выбор центра
    tennis_center_id = models.IntegerField(null=True, blank=True)

    # Шаг 2 - дата и время
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    duration_hours = models.IntegerField(null=True, blank=True)
    court_id = models.IntegerField(null=True, blank=True)

    # Шаг 3 - дополнительные услуги
    trainer_service = models.BooleanField(default=False)
    racket_rental = models.IntegerField(default=0)
    balls_rental = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_key}"
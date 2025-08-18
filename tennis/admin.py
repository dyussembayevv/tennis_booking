from django.contrib import admin
from .models import TennisCenter, TennisCourt, Booking, BookingSession


@admin.register(TennisCenter)
class TennisCenterAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone_number', 'number_of_courts', 'opening_time', 'closing_time']
    list_filter = ['opening_time', 'closing_time']
    search_fields = ['name', 'address']
    ordering = ['name']


class TennisCourtInline(admin.TabularInline):
    model = TennisCourt
    extra = 1


@admin.register(TennisCourt)
class TennisCourtAdmin(admin.ModelAdmin):
    list_display = ['tennis_center', 'court_number', 'price_per_hour', 'surface_type', 'indoor']
    list_filter = ['tennis_center', 'surface_type', 'indoor']
    search_fields = ['tennis_center__name', 'court_number']
    ordering = ['tennis_center', 'court_number']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'tennis_center', 'court', 'date', 'start_time',
        'duration_hours', 'total_price', 'status', 'created_at', 'id'
    ]
    list_filter = ['status', 'tennis_center', 'date', 'trainer_service', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'total_price']

    fieldsets = (
        ('Основная информация', {
            'fields': ('tennis_center', 'court', 'user', 'status')
        }),
        ('Время и дата', {
            'fields': ('date', 'start_time', 'duration_hours')
        }),
        ('Дополнительные услуги', {
            'fields': ('trainer_service', 'racket_rental', 'balls_rental')
        }),
        ('Контактные данные', {
            'fields': ('full_name', 'phone', 'email')
        }),
        ('Стоимость', {
            'fields': ('total_price',),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_paid', 'mark_as_cancelled']

    def mark_as_paid(self, request, queryset):
        """Действие для пометки бронирований как оплаченные"""
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} бронирований помечены как оплаченные.')

    mark_as_paid.short_description = "Пометить как оплаченное"

    def mark_as_cancelled(self, request, queryset):
        """Действие для отмены бронирований"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} бронирований отменены.')

    mark_as_cancelled.short_description = "Отменить бронирование"


@admin.register(BookingSession)
class BookingSessionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'user', 'tennis_center_id', 'date', 'created_at']
    list_filter = ['created_at', 'date']
    search_fields = ['session_key', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


# Настройка админки
admin.site.site_header = 'Управление теннисными кортами'
admin.site.site_title = 'Tennis Admin'
admin.site.index_title = 'Администрирование'
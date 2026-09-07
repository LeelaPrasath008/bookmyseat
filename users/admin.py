from django.contrib import admin
from .models import *

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'booking',
        'amount',
        'status',
        'transaction_id',
        'created_at'
    )

    list_filter = (
        'status',
        'created_at'
    )

    search_fields = (
        'user__username',
        'transaction_id'
    )

class MoviePosterInline(admin.TabularInline):
    model = MoviePoster
    extra = 1


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):

    inlines = [MoviePosterInline]

    list_display = (
        'title',
        'genre',
        'language',
        'average_rating',
        'release_date'
    )

    search_fields = (
        'title',
    )

    list_filter = (
        'genre',
        'language'
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'movie',
        'is_confirmed',
        'booking_date'
    )

    list_filter = (
        'is_confirmed',
        'booking_date'
    )

    search_fields = (
        'user__username',
        'movie__title'
    )

admin.site.register(Genre)
admin.site.register(Language)
admin.site.register(CastMember)
admin.site.register(Theater)
admin.site.register(ShowSchedule)
admin.site.register(Review)
admin.site.register(Seat)
admin.site.register(Wishlist)
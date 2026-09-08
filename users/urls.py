from . import views
from django.urls import path

from .views import (
    create_admin,
    movie_list,
    movie_detail,
    add_review,
    edit_review,
    report_review,
    seat_selection
)
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
urlpatterns = [
    path(
        'register/',
        views.register_view,
        name='register'
    ),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='users/login.html'
        ),
        name='login'
    ),

    path(
        '',
        movie_list,
        name='movie_list'
    ),

    path(
        'movie/<int:movie_id>/',
        movie_detail,
        name='movie_detail'
    ),

    path(
        'movie/<int:movie_id>/review/',
        add_review,
        name='add_review'
    ),

    path(
        'review/<int:review_id>/edit/',
        edit_review,
        name='edit_review'
    ),

    path(
        'review/<int:review_id>/report/',
        report_review,
        name='report_review'
    ),
    path(
        'schedule/<int:schedule_id>/seats/',
        seat_selection,
        name='seat_selection'
    ),
    path(
        'confirm_booking/',
        views.confirm_booking,
        name='confirm_booking'
    ),
    path(
        'release-seats/',
        views.release_reserved_seats,
        name='release_reserved_seats'
    ),
    path(
        'payment/<int:booking_id>/',
        views.create_payment,
        name='create_payment'
    ),
    path(
        'payment-success/',
        views.payment_success,
        name='payment_success'
    ),
    path(
        'booking-history/',
        views.booking_history,
        name='booking_history'
    ),
    path(
        'payment-failed/<int:payment_id>/',
        views.payment_failed,
        name='payment_failed'
    ),
    path(
        'razorpay/webhook/',
        views.razorpay_webhook,
        name='razorpay_webhook'
    ),
    path(
        'admin-dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),
    path(
        'export-bookings/',
        views.export_bookings_csv,
        name='export_bookings'
    ),
    path(
        'wishlist/add/<int:movie_id>/',
        views.add_to_wishlist,
        name='add_to_wishlist'
    ),

    path(
        'wishlist/',
        views.wishlist,
        name='wishlist'
    ),
    path(
        'wishlist/remove/<int:movie_id>/',
        views.remove_from_wishlist,
        name='remove_from_wishlist'
    ),
    path(
        'ticket/<int:booking_id>/',
        views.download_ticket,
        name='download_ticket'
    ),
    
    path(
        "logout/",
        LogoutView.as_view(next_page="login"),
        name="logout"
   ),
    path(
        'account/',
        views.account,
        name='account'
    ),
    path(
        'verify-ticket/<str:booking_ref>/',
        views.verify_ticket,
        name='verify_ticket'
    ),
    path(
        'test-payment-success/<int:payment_id>/',
        views.test_payment_success,
        name='test_payment_success'
    ),
    path('create-admin/', create_admin),
]
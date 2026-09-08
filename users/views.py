import csv
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
import traceback

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt

from .forms import RegisterForm, ReviewForm
from .models import (
    Booking,
    Genre,
    Language,
    Movie,
    Payment,
    Review,
    Seat,
    ShowSchedule,
    Theater,
    Wishlist,
)
from .tasks import send_ticket_email
from .utils import generate_ticket 


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


@staff_member_required
def export_bookings_csv(request):

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings.csv"'

    writer = csv.writer(response)
    writer.writerow(['User', 'Movie', 'Date'])

    bookings = Booking.objects.all()

    for booking in bookings:
        writer.writerow([
            booking.user.username,
            booking.movie.title,
            booking.booking_date,
        ])

    return response

@login_required
def download_ticket(request, booking_id):

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user,
    )

    if not booking.ticket_pdf:
        return HttpResponse("Ticket PDF not generated yet.")

    return FileResponse(
        booking.ticket_pdf.open('rb'),
        as_attachment=True,
    )


@staff_member_required
def admin_dashboard(request):

    today = timezone.now()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    payments = Payment.objects.filter(status='success')

    if start_date and end_date:
        payments = payments.filter(
            created_at__date__range=[start_date, end_date]
        )

    daily_revenue = Payment.objects.filter(
        status='success',
        created_at__date=today.date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    weekly_revenue = Payment.objects.filter(
        status='success',
        created_at__gte=today - timedelta(days=7)
    ).aggregate(total=Sum('amount'))['total'] or 0

    monthly_revenue = Payment.objects.filter(
        status='success',
        created_at__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0

    yearly_revenue = Payment.objects.filter(
        status='success',
        created_at__year=today.year
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_bookings = Booking.objects.count()
    total_users = User.objects.count()

    most_booked_movies = Booking.objects.values(
        'movie__title'
    ).annotate(total=Count('id')).order_by('-total')[:5]

    recent_users = User.objects.order_by('-date_joined')[:10]

    peak_hours = Booking.objects.annotate(
        hour=ExtractHour('booking_date')
    ).values('hour').annotate(total=Count('id')).order_by('-total')[:5]

    top_theaters = Booking.objects.values(
        'schedule__theater__name'
    ).annotate(total=Count('id')).order_by('-total')[:5]

    occupancy_data = []

    for theater in Theater.objects.all():

        total_seats = Seat.objects.filter(schedule__theater=theater).count()
        booked_seats = Seat.objects.filter(
            schedule__theater=theater,
            status='booked'
        ).count()

        occupancy = 0
        if total_seats > 0:
            occupancy = round((booked_seats / total_seats) * 100, 2)

        occupancy_data.append({'name': theater.name, 'occupancy': occupancy})

    cancelled_bookings = Booking.objects.filter(is_cancelled=True).count()
    refund_count = Payment.objects.filter(is_refunded=True).count()
    refund_amount = Payment.objects.filter(
        is_refunded=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    daily_bookings = Booking.objects.extra(
        {'day': "date(booking_date)"}
    ).values('day').annotate(total=Count('id')).order_by('-day')[:10]

    new_users_month = User.objects.filter(date_joined__month=today.month).count()

    return render(
        request,
        'users/admin_dashboard.html',
        {
            'daily_revenue': daily_revenue,
            'weekly_revenue': weekly_revenue,
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
            'total_bookings': total_bookings,
            'total_users': total_users,
            'most_booked_movies': most_booked_movies,
            'recent_users': recent_users,
            'peak_hours': peak_hours,
            'top_theaters': top_theaters,
            'cancelled_bookings': cancelled_bookings,
            'refund_count': refund_count,
            'refund_amount': refund_amount,
            'occupancy_data': occupancy_data,
            'daily_bookings': daily_bookings,
            'new_users_month': new_users_month,
        }
    )


@csrf_exempt
def razorpay_webhook(request):

    if request.method != "POST":
        return HttpResponseBadRequest()

    payload = request.body
    signature = request.headers.get("X-Razorpay-Signature", "")

    client = get_razorpay_client()
    try:
        client.utility.verify_webhook_signature(
            payload.decode("utf-8"), signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception:
        return HttpResponse(status=400)

    data = json.loads(payload)
    event = data.get("event")

    if event in ("payment.captured", "order.paid"):

        payment_entity = data["payload"]["payment"]["entity"]
        order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
        except Payment.DoesNotExist:
            return HttpResponse(status=200)

        _finalize_payment(payment, razorpay_payment_id, payment_entity)

    elif event == "payment.failed":

        payment_entity = data["payload"]["payment"]["entity"]
        order_id = payment_entity.get("order_id")

        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
            if payment.status == "pending":
                payment.status = "failed"
                payment.save()
                Seat.objects.filter(
                    reserved_by=payment.user,
                    schedule=payment.booking.schedule,
                    status="reserved",
                ).update(status="available", reserved_by=None, reserved_at=None)
        except Payment.DoesNotExist:
            pass

    return HttpResponse(status=200)

@login_required
def payment_failed(request, payment_id):

    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    if payment.status != "success":
        payment.status = "failed"
        payment.save()

        Seat.objects.filter(
            reserved_by=payment.user,
            schedule=payment.booking.schedule,
            status='reserved'
        ).update(
            status='available',
            reserved_by=None,
            reserved_at=None,
        )

    return redirect('booking_history')

@login_required
def booking_history(request):

    bookings = list(Booking.objects.filter(
        user=request.user
    ).order_by('-booking_date'))

    payments = Payment.objects.filter(
        user=request.user
    ).order_by('-created_at')

    latest_payment_by_booking = {}
    for p in payments:
        latest_payment_by_booking.setdefault(p.booking_id, p)

    for b in bookings:
        b.latest_payment = latest_payment_by_booking.get(b.id)
        b.can_retry = (not b.is_confirmed) and (not b.is_cancelled)

    return render(
        request,
        'users/booking_history.html',
        {
            'bookings': bookings,
            'payments': payments,
        }
    )


@login_required
@transaction.atomic
def create_payment(request, booking_id):

    booking = get_object_or_404(
        Booking.objects.select_for_update(),
        id=booking_id,
    )

    if booking.user != request.user:
        messages.error(request, "You can only pay for your own bookings.")
        return redirect('movie_list')

    if booking.is_confirmed:
        messages.info(request, "This booking is already paid for.")
        return redirect('booking_history')

    seat_count = len(
        booking.booked_seats.split(',')
    ) if booking.booked_seats else 1

    amount = (Decimal(booking.schedule.ticket_price) * seat_count).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    amount_paise = int((amount * 100).to_integral_value())

    client = get_razorpay_client()

    existing_payment = (
        Payment.objects.filter(booking=booking, status='pending')
        .order_by('-created_at')
        .first()
    )

    if existing_payment and existing_payment.razorpay_order_id:
        try:
            order = client.order.fetch(existing_payment.razorpay_order_id)
            if order.get('status') == 'created' and order.get('amount') == amount_paise:
                return render(
                    request,
                    "users/payment.html",
                    {
                        "payment": existing_payment,
                        "order": order,
                        "razorpay_key": settings.RAZORPAY_KEY_ID,
                    }
                )
        except Exception:
            pass

    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "booking_id": str(booking.id),
            "user_id": str(request.user.id),
        },
    })

    payment = Payment.objects.create(
        user=request.user,
        booking=booking,
        amount=amount,
        razorpay_order_id=order["id"],
        status="pending",
    )

    return render(
        request,
        "users/payment.html",
        {
            "payment": payment,
            "order": order,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
        }
    )


@transaction.atomic
def _finalize_payment(payment, razorpay_payment_id, remote_payment=None):
    print("FINALIZE PAYMENT STARTED")
    payment = Payment.objects.select_for_update().get(pk=payment.pk)

    if payment.status == "success":
        return True

    if remote_payment is not None:
        expected_paise = int((payment.amount * 100).to_integral_value())
        if remote_payment.get("amount") != expected_paise or remote_payment.get("currency") != "INR":
            print("PAYMENT AMOUNT MISMATCH", payment.id, remote_payment)
            return False
        if remote_payment.get("status") not in ("captured", "authorized"):
            return False

    payment.status = "success"
    payment.razorpay_payment_id = razorpay_payment_id
    payment.transaction_id = razorpay_payment_id
    payment.save()

    booking = payment.booking

    reserved_seats = Seat.objects.select_for_update().filter(
        reserved_by=payment.user,
        schedule=booking.schedule,
        status="reserved",
    )

    seat_numbers = ", ".join(reserved_seats.values_list("seat_number", flat=True))
    if seat_numbers:
        booking.booked_seats = seat_numbers

    booking.is_confirmed = True
    booking.booking_reference = booking.booking_reference or get_random_string(10)
    booking.payment_reference = razorpay_payment_id
    booking.save()

    reserved_seats.update(status="booked")

    try:
        pdf_dir = os.path.join(settings.MEDIA_ROOT, "tickets")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"ticket_{booking.id}.pdf")
        print("ABOUT TO GENERATE PDF")
        generate_ticket(booking, payment, pdf_path)
        booking.refresh_from_db()
        print("TICKET GENERATED")
    except Exception as e:
        print("PDF GENERATION ERROR:", str(e))
        traceback.print_exc()
    try:
        if booking.ticket_pdf:
            send_ticket_email.delay(payment.user.email, booking.ticket_pdf.path)
            print("EMAIL QUEUED")
    except Exception as e:
        print("EMAIL DISPATCH ERROR:", str(e))

    return True


def verify_ticket(request, booking_ref):

    booking = Booking.objects.filter(
        booking_reference=booking_ref,
        is_confirmed=True,
    ).first()

    return render(
        request,
        'users/verify_ticket.html',
        {'booking': booking}
    )


@login_required
def payment_success(request):
    print("SUCCESS VIEW HIT")
    payment_id = request.GET.get("payment_id")
    order_id = request.GET.get("order_id")
    signature = request.GET.get("signature")

    if not payment_id or not order_id or not signature:
        messages.error(request, "Invalid payment response.")
        return redirect("movie_list")

    payment = get_object_or_404(Payment, razorpay_order_id=order_id, user=request.user)

    if payment.status == "success":
        return redirect("booking_history")

    client = get_razorpay_client()

    params_dict = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError as e:
        print("RAZORPAY VERIFY ERROR:", str(e))
        messages.error(request, f"Payment verification failed: {e}")
        return redirect("movie_list")
    except Exception as e:
        print("RAZORPAY VERIFY ERROR:", str(e))
        messages.error(request, f"Payment verification failed: {e}")
        return redirect("movie_list")

    try:
        remote_payment = client.payment.fetch(payment_id)
    except Exception:
        remote_payment = None

    ok = _finalize_payment(payment, payment_id, remote_payment)

    if not ok:
        messages.error(request, "We couldn't confirm your payment amount. Please contact support.")
        return redirect("booking_history")

    messages.success(request, "Payment Successful! Your ticket has been generated.")
    return redirect("booking_history")


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('movie_list')
        else:
            print("FORM ERRORS:")
            print(form.errors)
    else:
        form = RegisterForm()

    return render(
        request,
        'users/register.html',
        {'form': form}
    )


@login_required
@transaction.atomic
def seat_selection(request, schedule_id):

    release_expired_seats()

    schedule = get_object_or_404(
        ShowSchedule,
        id=schedule_id
    )

    seats = Seat.objects.filter(
        schedule=schedule
    ).order_by('seat_number')

    if request.method == 'POST':

        selected = request.POST.getlist('seats')

        reserved_seats = []

        for seat_id in selected:

            seat = Seat.objects.select_for_update().get(
                id=seat_id
            )

            if seat.status == "available":

                seat.status = "reserved"
                seat.reserved_by = request.user
                seat.reserved_at = timezone.now()
                seat.save()

                reserved_seats.append(seat)

        if not reserved_seats:

            messages.error(
                request,
                "Selected seats are no longer available."
            )

            return redirect(
                "seat_selection",
                schedule_id=schedule_id
            )

        seat_numbers = ", ".join(
            seat.seat_number
            for seat in reserved_seats
        )

        booking = Booking.objects.create(
            user=request.user,
            movie=schedule.movie,
            schedule=schedule,
            booked_seats=seat_numbers,
        )

        return redirect(
            "create_payment",
            booking_id=booking.id
        )

    rows = list("ABCDEFGHIJ")

    seat_map = {}

    for row in rows:

        row_seats = []

        for seat in seats:

            if seat.seat_number.startswith(row):
                row_seats.append(seat)

        seat_map[row] = row_seats

    return render(
        request,
        "users/seat_selection.html",
        {
            "schedule": schedule,
            "seat_map": seat_map,
            "rows": rows,
        }
    )

def movie_list(request):

    movies = Movie.objects.all()

    search = request.GET.get('search')
    genre = request.GET.get('genre')
    language = request.GET.get('language')
    rating = request.GET.get('rating')
    release_year = request.GET.get('release_year')
    theater = request.GET.get('theater')
    city = request.GET.get('city')
    sort = request.GET.get('sort')

    if search:
        movies = movies.filter(Q(title__icontains=search))

    if genre:
        movies = movies.filter(genre__id=genre)

    if language:
        movies = movies.filter(language__id=language)

    if rating:
        movies = movies.filter(average_rating__gte=rating)

    if release_year:
        movies = movies.filter(release_date__year=release_year)

    if theater:
        movies = movies.filter(showschedule__theater__id=theater).distinct()

    if city:
        movies = movies.filter(showschedule__theater__location=city).distinct()

    if sort == "rating":
        movies = movies.order_by('-average_rating')
    elif sort == "newest":
        movies = movies.order_by('-release_date')
    elif sort == "title":
        movies = movies.order_by('title')
    elif sort == "popular":
        movies = movies.annotate(booking_count=Count('booking')).order_by('-booking_count')
    elif sort == "price_low":
        movies = movies.order_by('showschedule__ticket_price')
    elif sort == "price_high":
        movies = movies.order_by('-showschedule__ticket_price')

    movie_count = movies.count()

    genres = Genre.objects.all()
    languages = Language.objects.all()
    theaters = Theater.objects.all()

    cities = Theater.objects.values_list('location', flat=True).distinct()

    trending_movies = Movie.objects.annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')[:5]

    recent_movies = Movie.objects.order_by('-release_date')[:5]

    paginator = Paginator(movies, 8)

    page_number = request.GET.get('page')
    show_time = request.GET.get('show_time')

    if show_time:
        movies = movies.filter(
            showschedule__show_time__hour=show_time
        ).distinct()

    movies = paginator.get_page(page_number)

    is_filtering = any([
        search, genre, language, rating, release_year, theater, city, show_time,
    ])

    recommended_movies = Movie.objects.none()

    if request.user.is_authenticated and not is_filtering:

        booked_movies = Booking.objects.filter(
            user=request.user
        ).values_list('movie_id', flat=True)

        recommended_movies = Movie.objects.filter(
            genre__in=Movie.objects.filter(
                id__in=booked_movies
            ).values_list('genre', flat=True)
        ).exclude(id__in=booked_movies)[:6]

    available_show_times = ShowSchedule.objects.values_list('show_time', flat=True)

    recently_viewed_movies = Movie.objects.none()

    recent_ids = request.session.get('recently_viewed', [])

    if recent_ids:
        recently_viewed_movies = Movie.objects.filter(id__in=recent_ids)

    wishlist_count = 0

    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return render(
        request,
        'users/movie_list.html',
        {
            'movies': movies,
            'genres': genres,
            'languages': languages,
            'theaters': theaters,
            'cities': cities,
            'movie_count': movie_count,
            'trending_movies': trending_movies,
            'recent_movies': recent_movies,
            'recommended_movies': recommended_movies,
            'available_show_times': available_show_times,
            'recently_viewed_movies': recently_viewed_movies,
            'wishlist_count': wishlist_count,
        }
    )


def movie_detail(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    recently_viewed = request.session.get('recently_viewed', [])

    if movie.id not in recently_viewed:
        recently_viewed.insert(0, movie.id)
        recently_viewed = recently_viewed[:6]

    request.session['recently_viewed'] = recently_viewed

    similar_movies = Movie.objects.filter(
        genre=movie.genre,
        language=movie.language
    ).exclude(id=movie.id)[:4]

    recent_movies = Movie.objects.order_by('-release_date')[:4]

    trending_movies = Movie.objects.order_by('-average_rating')[:4]

    reviews = Review.objects.filter(movie=movie, reported=False)

    wishlist_count = 999

    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return render(
        request,
        'users/movie_detail.html',
        {
            'movie': movie,
            'reviews': reviews,
            'similar_movies': similar_movies,
            'recent_movies': recent_movies,
            'trending_movies': trending_movies,
            'wishlist_count': wishlist_count,
        }
    )


@login_required
def add_review(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    has_watched = Booking.objects.filter(
        user=request.user,
        movie=movie,
        watched=True
    ).exists()

    if not has_watched:
        return render(
            request,
            'users/error.html',
            {'message': 'You can review a movie only after watching it.'}
        )

    if request.method == 'POST':

        form = ReviewForm(request.POST)

        if form.is_valid():

            review = form.save(commit=False)
            review.movie = movie
            review.user = request.user
            review.verified_viewer = True
            review.save()

            reviews = Review.objects.filter(movie=movie)
            total = sum(r.rating for r in reviews)
            movie.average_rating = total / reviews.count()
            movie.save()

            return redirect('movie_detail', movie_id=movie.id)

    else:
        form = ReviewForm()

    return render(
        request,
        'users/add_review.html',
        {'form': form, 'movie': movie}
    )


@login_required
def edit_review(request, review_id):

    review = get_object_or_404(Review, id=review_id, user=request.user)

    if request.method == 'POST':

        form = ReviewForm(request.POST, instance=review)

        if form.is_valid():

            form.save()

            reviews = Review.objects.filter(movie=review.movie)
            total = sum(r.rating for r in reviews)
            review.movie.average_rating = total / reviews.count()
            review.movie.save()

            return redirect('movie_detail', movie_id=review.movie.id)

    else:
        form = ReviewForm(instance=review)

    return render(
        request,
        'users/edit_review.html',
        {'form': form, 'review': review}
    )


@login_required
def report_review(request, review_id):

    review = get_object_or_404(Review, id=review_id)
    review.reported = True
    review.save()

    return redirect('movie_detail', movie_id=review.movie.id)

@login_required
def confirm_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    has_paid = Payment.objects.filter(booking=booking, status='success').exists()

    if not has_paid:
        messages.error(request, "This booking has not been paid for yet.")
        return redirect('create_payment', booking_id=booking.id)

    Seat.objects.filter(
        schedule=booking.schedule,
        reserved_by=request.user,
        status='reserved',
    ).update(status='booked')

    booking.is_confirmed = True
    booking.save()

    return redirect('booking_history')


def release_expired_seats():

    expired = timezone.now() - timedelta(minutes=2)

    Seat.objects.filter(
        status='reserved',
        reserved_at__lt=expired
    ).update(
        status='available',
        reserved_by=None,
        reserved_at=None,
    )


@login_required
def release_reserved_seats(request):

    Seat.objects.filter(
        reserved_by=request.user,
        status='reserved',
    ).update(
        status='available',
        reserved_by=None,
        reserved_at=None,
    )

    return redirect(request.META.get('HTTP_REFERER') or 'movie_list')


@login_required
def add_to_wishlist(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    Wishlist.objects.get_or_create(user=request.user, movie=movie)

    messages.success(request, "Movie added to wishlist!")

    return redirect('movie_detail', movie_id=movie.id)

@login_required
def wishlist(request):

    wishlist_items = Wishlist.objects.filter(user=request.user)

    wishlist_count = wishlist_items.count()

    return render(
        request,
        'users/wishlist.html',
        {
            'wishlist_items': wishlist_items,
            'wishlist_count': wishlist_count,
        }
    )

@login_required
def remove_from_wishlist(request, movie_id):

    Wishlist.objects.filter(
        user=request.user,
        movie_id=movie_id
    ).delete()

    messages.success(request, "Movie removed from wishlist!")

    return redirect('wishlist')

@login_required
def account(request):

    bookings = Booking.objects.filter(
        user=request.user
    ).order_by('-booking_date')

    wishlist_items = Wishlist.objects.filter(user=request.user)

    context = {
        'bookings_count': bookings.count(),
        'wishlist_count': wishlist_items.count(),
        'reviews_count': Review.objects.filter(user=request.user).count(),
        'watched_count': Booking.objects.filter(user=request.user, watched=True).count(),
        'recent_bookings': bookings[:4],
        'wishlist_items': wishlist_items[:6],
    }

    return render(request, 'users/account.html', context)


@login_required
def cancel_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    booking.is_cancelled = True
    booking.save()

    payment = Payment.objects.filter(booking=booking, status="success").first()

    if payment:
        payment.is_refunded = True
        payment.save()

    messages.success(request, "Booking cancelled successfully.")

    return redirect("booking_history")
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils.crypto import get_random_string

@login_required
def test_payment_success(request, payment_id):

    payment = get_object_or_404(
        Payment,
        id=payment_id
    )

    _finalize_payment(
        payment,
        "TEST_TXN_123456"
    )

    messages.success(
        request,
        "Test Payment Successful"
    )

    return redirect("booking_history")
from django.http import HttpResponse
from django.contrib.auth.models import User

def create_admin(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            email="admin@gmail.com",
            password="Admin@123"
        )
        return HttpResponse("Admin Created Successfully")

    return HttpResponse("Admin Already Exists")
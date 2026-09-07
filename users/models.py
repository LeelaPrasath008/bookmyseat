from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class CastMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=200)
    genre = models.ForeignKey('Genre', on_delete=models.CASCADE)
    language = models.ForeignKey('Language', on_delete=models.CASCADE)

    description = models.TextField()

    duration = models.IntegerField()

    certification = models.CharField(
        max_length=20,
        default='U/A'
    )

    release_date = models.DateField()

    trailer_url = models.URLField()

    average_rating = models.FloatField(
        default=0
    )

    cast = models.ManyToManyField(
        'CastMember',
        blank=True
    )

    def __str__(self):
        return self.title


class MoviePoster(models.Model):
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name='posters'
    )

    image = models.ImageField(
        upload_to='movie_posters/'
    )

    def __str__(self):
        return self.movie.title


class Theater(models.Model):

    name = models.CharField(max_length=200)

    location = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class ShowSchedule(models.Model):

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    theater = models.ForeignKey(
        Theater,
        on_delete=models.CASCADE
    )

    show_time = models.DateTimeField()
    ticket_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=200
    )

    def __str__(self):
        return f"{self.movie.title} - {self.show_time}"


class Seat(models.Model):

    STATUS_CHOICES = (
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked'),
    )

    schedule = models.ForeignKey(
        ShowSchedule,
        on_delete=models.CASCADE,
        related_name='seats'
    )

    seat_number = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )

    reserved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    reserved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['seat_number']

    def __str__(self):
        return self.seat_number


class Booking(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['booking_date']),
            models.Index(fields=['movie']),
            models.Index(fields=['schedule']),
            models.Index(fields=['user']),
        ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    schedule = models.ForeignKey(
        ShowSchedule,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    watched = models.BooleanField(
        default=False
    )

    is_cancelled = models.BooleanField(
        default=False
    )

    booking_date = models.DateTimeField(
        auto_now_add=True
    )

    is_confirmed = models.BooleanField(
        default=False
    )

    booking_reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    # Seats booked (A1,A2,A3)
    booked_seats = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Payment reference from Razorpay
    payment_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Generated PDF Ticket
    ticket_pdf = models.FileField(
        upload_to='tickets/',
        blank=True,
        null=True
    )

    # QR Code Image
    qr_code = models.ImageField(
        upload_to='qr_codes/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


class Payment(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    is_refunded = models.BooleanField(
        default=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    razorpay_order_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True
    )

    transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class Review(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    rating = models.IntegerField()

    comment = models.TextField()

    verified_viewer = models.BooleanField(
        default=False
    )

    reported = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


class Wishlist(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"

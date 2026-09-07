from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ShowSchedule, Seat


@receiver(post_save, sender=ShowSchedule)
def create_seats(sender, instance, created, **kwargs):

    if created:

        rows = "ABCDEFGHIJ"

        for row in rows:
            for num in range(1, 11):

                Seat.objects.create(
                    schedule=instance,
                    seat_number=f"{row}{num}"
                )
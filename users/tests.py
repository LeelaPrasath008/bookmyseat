from django.test import TestCase
from .models import Genre

class GenreTest(TestCase):

    def test_genre_creation(self):

        genre = Genre.objects.create(
            name="Action"
        )

        self.assertEqual(
            genre.name,
            "Action"
        )
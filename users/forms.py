from django import forms
from .models import Review
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):

    email = forms.EmailField()

    class Meta:
        model = User

        fields = [
            'username',
            'email',
            'password1',
            'password2'
        ]
        
class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review

        fields = [
            'rating',
            'comment'
        ]

        widgets = {

            'rating': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'max': 5
                }
            ),

            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'Write your review...'
                }
            )
        }
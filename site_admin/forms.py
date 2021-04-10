from django import forms
from authentication.models import User

class EditUserProfile(forms.ModelForm):

    class Meta:
        model = User
        exclude = ['password', 'role', 'last_login', 'is_active', 'campus']
        widgets = {
            'register_date': forms.DateInput(attrs={'readonly': True}),
            'rating': forms.TextInput(attrs={'readonly': True}),
        }

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        name = cleaned_data.get('name')
        if (not username) or (not name)  or (not email):
            raise forms.ValidationError("Please correct the errors below.")

        return cleaned_data


class AddUser(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'name', 'email']

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')

        if (not username) or (not name) or (not email):
            raise forms.ValidationError("Please correct the errors below.")

        return cleaned_data


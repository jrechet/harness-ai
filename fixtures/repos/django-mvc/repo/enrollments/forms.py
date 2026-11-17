from django import forms


class EnrollmentForm(forms.Form):
    full_name = forms.CharField(label="Full name", max_length=200)
    email = forms.EmailField(label="E-mail address")

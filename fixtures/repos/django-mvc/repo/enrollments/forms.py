from django import forms


class EnrollmentForm(forms.Form):
    full_name = forms.CharField(label="Nom et prénom", max_length=200)
    email = forms.EmailField(label="Adresse e-mail")

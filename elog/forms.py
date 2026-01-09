from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import Logbook


class SignUpForm(UserCreationForm):
    """
    Custom Signup Form with Email, Name, and Group selection.
    """
    email = forms.EmailField(required=True, help_text='Required. Enter a valid email address.')
    first_name = forms.CharField(max_length=30, required=True, help_text='Your given name')
    last_name = forms.CharField(max_length=30, required=True, help_text='Your family name')

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        # [Modified] Change widget to SelectMultiple and add a specific class for JS targeting
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-multi', 
            'style': 'width: 100%'
        }),
        required=True,
        help_text="Select your team(s). You can search and select multiple."
    )

    class Meta:
        model = User
        # 'groups' 필드 추가
        fields = ('username', 'email', 'last_name', 'first_name', 'groups')


class LogbookForm(forms.ModelForm):
    class Meta:
        model = Logbook
        # Included 'allowed_groups' in the fields list
        fields = ['name', 'description', 'access_level', 'allowed_groups']

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            # Use checkboxes for selecting multiple groups easily
            'allowed_groups': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap styling to form fields
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update(
            {'class': 'form-control'})
        self.fields['access_level'].widget.attrs.update(
            {'class': 'form-select'})

        # Optional: You can filter groups here if you only want to show groups the user belongs to

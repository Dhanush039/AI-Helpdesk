from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import Ticket, TicketComment, Profile


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    department = forms.CharField(required=False, max_length=100)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        user = super().save(commit)
        Profile.objects.update_or_create(
            user=user,
            defaults={"role": Profile.Role.EMPLOYEE, "department": self.cleaned_data.get("department", "")},
        )
        return user


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Short summary of the issue"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5,
                                                   "placeholder": "Describe the issue in detail..."}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Add a comment..."}),
        }


class AssistantQuestionForm(forms.Form):
    question = forms.CharField(
        label="",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3,
                                      "placeholder": "e.g. How do I troubleshoot DNS issues on Windows?"}),
    )


class TicketAssignForm(forms.Form):
    agent = forms.ModelChoiceField(queryset=User.objects.none(), required=True,
                                    widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agent"].queryset = User.objects.filter(profile__role=Profile.Role.L1_AGENT)

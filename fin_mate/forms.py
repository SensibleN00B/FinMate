from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from fin_mate.models import Account, Budget, Category, Tag, Transaction


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name", "currency", "type"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Cash / Monobank / Savings",
                }
            ),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "type": forms.Select(attrs={"class": "form-select"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Groceries / Rent / Salary",
                }
            )
        }


class TransactionForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="Choose one or more tags.",
    )

    class Meta:
        model = Transaction
        fields = ["amount", "type", "account", "category", "date", "description"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "type": forms.Select(attrs={"class": "form-select"}),
            "account": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["tags"].widget.attrs.update({"class": "form-check-input"})

        if user is not None:
            self.fields["account"].queryset = self.fields["account"].queryset.filter(
                user=user
            )
            self.fields["category"].queryset = self.fields["category"].queryset.filter(
                user=user
            )
            self.fields["tags"].queryset = Tag.objects.filter(user=user).order_by(
                "name"
            )


class TransactionFilterForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label="All categories",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    tag = forms.ModelChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        empty_label="All tags",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    type = forms.ChoiceField(
        required=False,
        choices=(("", "All types"),) + tuple(Transaction.TransactionType.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("date_desc", "Date ↓"),
            ("date_asc", "Date ↑"),
            ("amount_desc", "Amount ↓"),
            ("amount_asc", "Amount ↑"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            if "category" in self.fields:
                self.fields["category"].queryset = Category.objects.filter(
                    user=user
                ).order_by("name")
            if "tag" in self.fields:
                self.fields["tag"].queryset = Tag.objects.filter(user=user).order_by(
                    "name"
                )
        if "sort" not in self.data:
            self.fields["sort"].initial = "-date"


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Travel / Repair / Car",
                }
            ),
            "color": forms.Select(attrs={"class": "form-select"}),
        }


class BudgetForm(forms.ModelForm):
    period = forms.DateField(
        input_formats=["%Y-%m", "%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "form-control", "type": "month"}),
        help_text="Select month and year; day is ignored (set to the 1st).",
    )

    class Meta:
        model = Budget
        fields = ["category", "limit", "period", "notes"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "limit": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional notes",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = self.fields["category"].queryset.filter(
                user=user
            )
        if self.instance and self.instance.pk and self.instance.period:
            self.initial["period"] = self.instance.period.replace(day=1)

    def clean_period(self):
        value = self.cleaned_data["period"]
        return value.replace(day=1)

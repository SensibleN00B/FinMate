from django import forms

from fin_mate.models import Budget


class BudgetForm(forms.ModelForm):
    period = forms.DateField(
        input_formats=["%Y-%m"],
        widget=forms.DateInput(attrs={"type": "month", "class": "form-control"}),
        label="month",
    )

    class Meta:
        model = Budget
        fields = ("category", "limit", "period", "notes")

    def clean_period(self):
        date = self.cleaned_data["period"]
        return date.replace(day=1)

from datetime import date
from decimal import Decimal
from calendar import monthrange

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.db.models import DecimalField, Prefetch, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import AccountForm, BudgetForm, CategoryForm, TagForm, TransactionForm
from .models import Account, Budget, Category, Tag, Transaction, TransactionTag
from .services.fx import get_rates


def _first_day(dt: date) -> date:
    return dt.replace(day=1)


def _prev_month(first_day: date) -> date:
    return first_day.replace(year=first_day.year - 1, month=12) if first_day.month == 1 \
        else first_day.replace(month=first_day.month - 1)


class UserOwnedQuerysetMixin(LoginRequiredMixin):
    """Restrict queryset to the current user's objects."""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class AccountListView(UserOwnedQuerysetMixin, ListView):
    model = Account
    paginate_by = 5
    context_object_name = "accounts"
    template_name = "fin_mate/account_list.html"


class AccountDetailView(UserOwnedQuerysetMixin, DetailView):
    model = Account
    context_object_name = "account"
    template_name = "fin_mate/account_detail.html"


class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = "fin_mate/account_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error(
                "name", "Account with this name already exists for your user."
            )
            return self.form_invalid(form)
        messages.success(self.request, "Account created ✅")
        return response

    def get_success_url(self):
        return reverse("fin_mate:account-detail", kwargs={"pk": self.object.pk})


class AccountUpdateView(UserOwnedQuerysetMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "fin_mate/account_form.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error(
                "name", "Account with this name already exists for your user."
            )
            return self.form_invalid(form)
        messages.success(self.request, "Account updated ✍️")
        return response

    def get_success_url(self):
        return reverse("fin_mate:account-detail", kwargs={"pk": self.object.pk})


class AccountDeleteView(UserOwnedQuerysetMixin, DeleteView):
    model = Account
    success_url = reverse_lazy("fin_mate:account-list")
    template_name = "fin_mate/account_confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Account deleted 🗑️")
        return super().delete(request, *args, **kwargs)


class CategoryListView(UserOwnedQuerysetMixin, ListView):
    model = Category
    paginate_by = 7
    context_object_name = "categories"
    template_name = "fin_mate/category_list.html"


class CategoryDetailView(UserOwnedQuerysetMixin, DetailView):
    model = Category
    context_object_name = "category"
    template_name = "fin_mate/category_detail.html"


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "fin_mate/category_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("name", "This category already exists for you.")
            return self.form_invalid(form)
        messages.success(self.request, "Category created ✅")
        return response

    def get_success_url(self):
        return reverse("fin_mate:category-detail", kwargs={"pk": self.object.pk})


class CategoryUpdateView(UserOwnedQuerysetMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "fin_mate/category_form.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("name", "This category already exists for you.")
            return self.form_invalid(form)
        messages.success(self.request, "Category updated ✍️")
        return response

    def get_success_url(self):
        return reverse("fin_mate:category-detail", kwargs={"pk": self.object.pk})


class CategoryDeleteView(UserOwnedQuerysetMixin, DeleteView):
    model = Category
    success_url = reverse_lazy("fin_mate:category-list")
    template_name = "fin_mate/category_confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Category deleted 🗑️")
        return super().delete(request, *args, **kwargs)


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    paginate_by = 7
    context_object_name = "transactions"
    template_name = "fin_mate/transaction_list.html"

    def get_queryset(self):
        return (
            Transaction.objects.select_related("account", "category")
            .prefetch_related("transactiontag_set__tag")
            .filter(account__user=self.request.user)
            .order_by("-date", "-pk")
        )


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = Transaction
    context_object_name = "transaction"
    template_name = "fin_mate/transaction_detail.html"

    def get_queryset(self):
        return (
            Transaction.objects.select_related("account", "category")
            .prefetch_related("transactiontag_set__tag")
            .filter(account__user=self.request.user)
        )


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "fin_mate/transaction_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        cat_id = self.request.GET.get("category")
        dt = self.request.GET.get("date")

        if cat_id:
            initial["category"] = cat_id
            initial["type"] = Transaction.TransactionType.EXPENSE
        if dt:
            initial["date"] = dt
        return initial

    @db_transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        selected_tags = form.cleaned_data.get("tags")
        if selected_tags:
            TransactionTag.objects.filter(transaction=self.object).delete()
            TransactionTag.objects.bulk_create(
                [
                    TransactionTag(
                        transaction=self.object, tag=t, added_by=self.request.user
                    )
                    for t in selected_tags
                ]
            )
        messages.success(self.request, "Transaction created ✅")
        return response

    def get_success_url(self):
        return reverse("fin_mate:transaction-detail", kwargs={"pk": self.object.pk})


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "fin_mate/transaction_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.object:
            initial["tags"] = list(self.object.tags.values_list("pk", flat=True))
        return initial

    @db_transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        # replace existing tag links with the selected ones
        TransactionTag.objects.filter(transaction=self.object).delete()
        selected_tags = form.cleaned_data.get("tags") or []
        TransactionTag.objects.bulk_create(
            [
                TransactionTag(
                    transaction=self.object, tag=t, added_by=self.request.user
                )
                for t in selected_tags
            ]
        )
        messages.success(self.request, "Transaction updated ✍️")
        return response

    def get_queryset(self):
        return Transaction.objects.filter(account__user=self.request.user)

    def get_success_url(self):
        return reverse("fin_mate:transaction-detail", kwargs={"pk": self.object.pk})


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    success_url = reverse_lazy("fin_mate:transaction-list")
    template_name = "fin_mate/transaction_confirm_delete.html"

    def get_queryset(self):
        return Transaction.objects.filter(account__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Transaction deleted 🗑️")
        return super().delete(request, *args, **kwargs)


class TagListView(LoginRequiredMixin, ListView):
    model = Tag
    paginate_by = 10
    context_object_name = "tags"
    template_name = "fin_mate/tag_list.html"

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user).order_by("name")


class TagDetailView(LoginRequiredMixin, DetailView):
    model = Tag
    context_object_name = "tag"
    template_name = "fin_mate/tag_detail.html"

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class TagCreateView(LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = "fin_mate/tag_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("name", "Tag with this name already exists for you.")
            return self.form_invalid(form)
        messages.success(self.request, "Tag created ✅")
        return response

    def get_success_url(self):
        return reverse("fin_mate:tag-detail", kwargs={"pk": self.object.pk})


class TagUpdateView(LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = "fin_mate/tag_form.html"

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("name", "Tag with this name already exists for you.")
            return self.form_invalid(form)
        messages.success(self.request, "Tag updated ✍️")
        return response

    def get_success_url(self):
        return reverse("fin_mate:tag-detail", kwargs={"pk": self.object.pk})


class TagDeleteView(LoginRequiredMixin, DeleteView):
    model = Tag
    success_url = reverse_lazy("fin_mate:tag-list")
    template_name = "fin_mate/tag_confirm_delete.html"

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tag deleted 🗑️")
        return super().delete(request, *args, **kwargs)


class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    paginate_by = 5
    context_object_name = "budgets"
    template_name = "fin_mate/budget_list.html"

    def get_queryset(self):
        qs = (
            Budget.objects.select_related("category")
            .filter(user=self.request.user)
            .order_by("-period", "category__name")
        )
        self._selected = None
        period = self.request.GET.get("period")
        if period:
            try:
                y, m = map(int, period.split("-")[:2])
                self._selected = date(y, m, 1)
                qs = qs.filter(period__year=y, period__month=m)
            except Exception:
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self._selected or _first_day(timezone.localdate())
        prev = _prev_month(selected)

        context["period"] = selected
        context["period_str"] = selected.strftime("%Y-%m")
        context["prev_period_str"] = prev.strftime("%Y-%m")
        context["has_budgets"] = context["paginator"].count > 0 if "paginator" in context else False
        return context


class BudgetDetailView(LoginRequiredMixin, DetailView):
    model = Budget
    context_object_name = "budget"
    template_name = "fin_mate/budget_detail.html"

    def get_queryset(self):
        return Budget.objects.select_related("category").filter(user=self.request.user)


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = "fin_mate/budget_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Budget for this category and month already exists.")
            return self.form_invalid(form)
        messages.success(self.request, "Budget created ✅")
        return response

    def get_success_url(self):
        return reverse("fin_mate:budget-detail", kwargs={"pk": self.object.pk})


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = "fin_mate/budget_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Budget for this category and month already exists.")
            return self.form_invalid(form)
        messages.success(self.request, "Budget updated ✍️")
        return response

    def get_success_url(self):
        return reverse("fin_mate:budget-detail", kwargs={"pk": self.object.pk})


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    success_url = reverse_lazy("fin_mate:budget-list")
    template_name = "fin_mate/budget_confirm_delete.html"

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Budget deleted 🗑️")
        return super().delete(request, *args, **kwargs)


class BudgetCopyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        period_param = request.POST.get("period")
        target = _first_day(timezone.localdate())
        if period_param:
            try:
                y, m = map(int, period_param.split("-")[:2])
                target = date(y, m, 1)
            except Exception:
                pass
        prev = _prev_month(target)

        prev_qs = (Budget.objects
                   .filter(user=request.user, period__year=prev.year, period__month=prev.month)
                   .select_related("category"))
        existing = set(Budget.objects
                       .filter(user=request.user, period__year=target.year, period__month=target.month)
                       .values_list("category_id", flat=True))
        to_create = [Budget(user=request.user, category=b.category, limit=b.limit, period=target, notes=b.notes)
                     for b in prev_qs if b.category_id not in existing]
        Budget.objects.bulk_create(to_create, ignore_conflicts=True)

        created = len(to_create)
        if created:
            messages.success(
                request,
                f"Copied {created} budget(s) from {prev:%Y-%m} to {target:%Y-%m}."
            )
        else:
            messages.info(
                request,
                f"Nothing to copy, or budgets already exist for {target:%Y-%m}."
            )

        return redirect(f"{reverse('fin_mate:budget-list')}?period={target:%Y-%m}")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "fin_mate/dashboard.html"

    @staticmethod
    def _month_range(dt: date) -> tuple[date, date]:
        start = dt.replace(day=1)
        end = start.replace(year=start.year + 1, month=1) if start.month == 12 \
            else start.replace(month=start.month + 1)
        return start, end

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        period_param = self.request.GET.get("period")
        if period_param:
            try:
                y, m = map(int, period_param.split("-")[:2])
                selected = date(y, m, 1)
            except Exception:
                selected = timezone.localdate().replace(day=1)
        else:
            selected = timezone.localdate().replace(day=1)
        start, end = self._month_range(selected)

        accounts_qs = Account.objects.with_balance().filter(user=user).order_by("name")

        month_tx = Transaction.objects.filter(
            account__user=user, date__gte=start, date__lt=end
        )

        currencies = {(a.currency or "").upper() for a in accounts_qs if a.currency}
        currencies |= {
            (row["account__currency"] or settings.FX_BASE_CURRENCY).upper()
            for row in month_tx.values("account__currency").distinct()
        }
        rates = get_rates(currencies)

        base_total = Decimal("0")
        acc_labels, acc_values_base = [], []
        for a in accounts_qs:
            amount = getattr(a, "annotated_balance", Decimal("0")) or Decimal("0")
            code = (a.currency or settings.FX_BASE_CURRENCY).upper()
            rate = rates.get(code, Decimal("1"))
            v_base = (amount * rate).quantize(Decimal("0.01"))
            base_total += v_base
            acc_labels.append(a.name)
            acc_values_base.append(float(v_base))

        def sum_in_base(qs) -> Decimal:
            total = Decimal("0")
            for row in qs.values("account__currency").annotate(total=Sum("amount")):
                code = (row["account__currency"] or settings.FX_BASE_CURRENCY).upper()
                rate = rates.get(code, Decimal("1"))
                total += (row["total"] * rate).quantize(Decimal("0.01"))
            return total

        income = sum_in_base(month_tx.filter(type=Transaction.TransactionType.INCOME))
        expenses = sum_in_base(month_tx.filter(type=Transaction.TransactionType.EXPENSE))
        net = income - expenses

        top_cats_qs = (
            month_tx.filter(type=Transaction.TransactionType.EXPENSE)
            .values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )
        total_exp = expenses or Decimal("0")
        top_categories = [
            {
                "name": row["category__name"] or "—",
                "total": row["total"],
                "percent": float((row["total"] / total_exp) * 100) if total_exp else 0.0,
            }
            for row in top_cats_qs
        ]

        budgets_qs = (
            Budget.objects.select_related("category")
            .filter(user=user, period__year=start.year, period__month=start.month)
            .order_by("category__name")
        )
        spends_map = {
            row["category_id"]: row["total"]
            for row in month_tx.filter(type=Transaction.TransactionType.EXPENSE)
            .values("category_id")
            .annotate(total=Sum("amount"))
        }
        budgets = []
        for b in budgets_qs:
            spent = spends_map.get(b.category_id, Decimal("0"))
            limit = b.limit or Decimal("0")
            progress = float((spent / (limit or Decimal("0.01"))) * 100) if limit else 0.0
            budgets.append({"obj": b, "spent": spent, "progress": progress})

        recent = (
            Transaction.objects.select_related("account", "category")
            .filter(account__user=user)
            .order_by("-date", "-pk")[:10]
        )

        context.update({
            "period": selected,
            "period_str": selected.strftime("%Y-%m"),

            "accounts": accounts_qs,
            "base_currency": settings.FX_BASE_CURRENCY,
            "total_balance": base_total,

            "accounts_chart": {
                "labels": acc_labels,
                "values": acc_values_base,
                "total": float(base_total),
            },

            "income": income,
            "expenses": expenses,
            "net": net,
            "top_categories": top_categories,
            "budgets": budgets,
            "recent": recent,
        })
        return context

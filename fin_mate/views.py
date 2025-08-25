from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.db.models import DecimalField, Prefetch, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse, reverse_lazy
from django.utils import timezone
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
        period = self.request.GET.get("period")
        if period:
            try:
                year, month = map(int, period.split("-")[:2])
                qs = qs.filter(period__year=year, period__month=month)
            except Exception:
                pass
        return qs


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


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "fin_mate/dashboard.html"

    @staticmethod
    def _month_range(dt: date) -> tuple[date, date]:
        start = dt.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
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
        total_balance = accounts_qs.aggregate(
            total=Coalesce(
                Sum("annotated_balance"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"] or Decimal("0")

        month_tx = Transaction.objects.filter(
            account__user=user, date__gte=start, date__lt=end
        )
        income = month_tx.filter(type=Transaction.TransactionType.INCOME).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
        expenses = month_tx.filter(type=Transaction.TransactionType.EXPENSE).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
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
                "percent": (
                    float((row["total"] / total_exp) * 100) if total_exp else 0.0
                ),
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
            limit = b.limit or Decimal("0.01")
            progress = float((spent / limit) * 100) if limit else 0.0
            budgets.append({"obj": b, "spent": spent, "progress": progress})

        recent = (
            Transaction.objects.select_related("account", "category")
            .filter(account__user=user)
            .order_by("-date", "-pk")[:10]
        )

        context.update(
            {
                "period": selected,
                "period_str": selected.strftime("%Y-%m"),
                "accounts": accounts_qs,
                "total_balance": total_balance,
                "income": income,
                "expenses": expenses,
                "net": net,
                "top_categories": top_categories,
                "budgets": budgets,
                "recent": recent,
            }
        )
        return context

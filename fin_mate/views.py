from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.db import transaction as db_transaction
from django.db.models import Prefetch, Q
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

from .forms import (
    AccountForm,
    BudgetForm,
    CategoryForm,
    TagForm,
    TransactionForm,
    TransactionFilterForm,
)
from .models import Account, Budget, Category, Tag, Transaction, TransactionTag
from .services.budget_copy import copy_month
from .services.budget_list import first_day, prev_month
from .services.dashboard import month_summary
from .services.dates import parse_period_or_today, month_range
from .services.mixins import UserOwnedQuerysetMixin


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
        try:
            with transaction.atomic():
                account = form.save(commit=False)
                account.user = self.request.user
                account.save()
                starting_balance = form.cleaned_data.get("starting_balance") or Decimal("0")

                if starting_balance > 0:
                    opening_category, _ = Category.objects.get_or_create(
                        user=self.request.user,
                        name="Opening balance",
                        defaults={"is_system": True},
                    )
                    if not opening_category.is_system:
                        opening_category.is_system = True
                        opening_category.save(update_fields=["is_system"])
                    Transaction.objects.create(
                        amount=starting_balance,
                        type=Transaction.TransactionType.INCOME,
                        account=account,
                        category=opening_category,
                        date=timezone.localdate(),
                        description="Initial balance",
                    )
                self.object = account

        except IntegrityError:
            form.add_error("name", "Account with this name already exists for your user.")
            return self.form_invalid(form)

        messages.success(self.request, "Account created ✅")
        return redirect(self.get_success_url())

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
    context_object_name = "transactions"
    template_name = "fin_mate/transaction_list.html"
    paginate_by = 10

    ORDER_ALLOWED = {"date_desc", "date_asc", "amount_desc", "amount_asc"}
    ORDER_MAP = {
        "date_desc": "-date",
        "date_asc": "date",
        "amount_desc": "-amount",
        "amount_asc": "amount",
    }
    LEGACY_MAP = {
        "-date": "date_desc",
        "date": "date_asc",
        "-amount": "amount_desc",
        "amount": "amount_asc",
    }

    def get_form(self):
        return TransactionFilterForm(self.request.GET or None, user=self.request.user)

    def base_queryset(self):
        return (
            Transaction.objects
            .public()
            .select_related("account", "category")
            .only(
                "id", "date", "amount", "type", "description",
                "account__id", "account__name", "account__currency",
                "category__id", "category__name",
            )
            .prefetch_related(
                Prefetch(
                    "transactiontag_set",
                    queryset=(
                        TransactionTag.objects
                        .select_related("tag")
                        .only(
                            "id", "transaction_id", "tag_id",
                            "tag__id", "tag__name", "tag__color",
                        )
                        .order_by("tag__name")
                    ),
                )
            )
            .filter(account__user=self.request.user)
        )

    def get_queryset(self):
        filtered_queryset = self.base_queryset()
        self.filter_form = form = self.get_form()

        if form.is_valid():
            cleaned_data = form.cleaned_data

            date_q = Q()
            if cleaned_data.get("date_from"):
                date_q &= Q(date__gte=cleaned_data["date_from"])
            if cleaned_data.get("date_to"):
                date_q &= Q(date__lte=cleaned_data["date_to"])
            if date_q:
                filtered_queryset = filtered_queryset.filter(date_q)

            if cleaned_data.get("category"):
                filtered_queryset = filtered_queryset.filter(category=cleaned_data["category"])

            if cleaned_data.get("tag"):
                filtered_queryset = filtered_queryset.filter(tags=cleaned_data["tag"]).distinct()

            if cleaned_data.get("type"):
                filtered_queryset = filtered_queryset.filter(type=cleaned_data["type"])

        raw_sort = (self.request.GET.get("sort") or "").strip()
        order_key = self.LEGACY_MAP.get(raw_sort, raw_sort)
        if order_key not in self.ORDER_ALLOWED:
            order_key = "date_desc"
        self.current_sort = order_key

        return filtered_queryset.order_by(self.ORDER_MAP[order_key], "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["current_sort"] = getattr(self, "current_sort", "date_desc")
        return context


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
        selected_date = self.request.GET.get("date")

        if cat_id:
            initial["category"] = cat_id
            initial["type"] = Transaction.TransactionType.EXPENSE
        if selected_date:
            initial["date"] = selected_date
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
    paginate_by = 7
    context_object_name = "budgets"
    template_name = "fin_mate/budget_list.html"

    def get_queryset(self):
        qs = (
            Budget.objects.select_related("category")
            .filter(user=self.request.user)
            .order_by("-period", "category__name")
        )

        self._selected = None
        raw = self.request.GET.get("period")
        if raw:
            try:
                y, m = map(int, raw.split("-")[:2])
                self._selected = date(y, m, 1)
            except Exception:
                pass

        if not self._selected:
            self._selected = first_day(timezone.localdate())

        return qs.filter(
            period__year=self._selected.year,
            period__month=self._selected.month,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self._selected
        prev = prev_month(selected)

        context["period"] = selected
        context["period_str"] = selected.strftime("%Y-%m")
        context["prev_period_str"] = prev.strftime("%Y-%m")
        context["has_budgets"] = bool(
            context.get("paginator")
            and context["paginator"].count > 0
        )
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
        target = parse_period_or_today(request.POST.get("period"))
        result = copy_month(request.user, target)

        if result.created:
            messages.success(
                request,
                f"Copied {result.created} budget(s) from {result.prev:%Y-%m} to {result.target:%Y-%m}.",
            )
        else:
            messages.info(
                request,
                f"Nothing to copy, or budgets already exist for {result.target:%Y-%m}.",
            )

        return redirect(f"{reverse('fin_mate:budget-list')}?period={target:%Y-%m}")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "fin_mate/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected = parse_period_or_today(self.request.GET.get("period"))
        start, end = month_range(selected)

        summary = month_summary(self.request.user, start, end)

        context.update(
            {
                "period": selected,
                "period_str": selected.strftime("%Y-%m"),
                "base_currency": settings.FX_BASE_CURRENCY,
                **summary,
            }
        )
        return context

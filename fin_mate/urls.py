from django.urls import path

from fin_mate.views import (
    AccountCreateView,
    AccountDeleteView,
    AccountDetailView,
    AccountListView,
    AccountUpdateView,
    BudgetCreateView,
    BudgetDeleteView,
    BudgetDetailView,
    BudgetListView,
    BudgetUpdateView,
    CategoryCreateView,
    CategoryDeleteView,
    CategoryDetailView,
    CategoryListView,
    CategoryUpdateView,
    DashboardView,
    TagCreateView,
    TagDeleteView,
    TagDetailView,
    TagListView,
    TagUpdateView,
    TransactionCreateView,
    TransactionDeleteView,
    TransactionDetailView,
    TransactionListView,
    TransactionUpdateView, BudgetCopyView,
)

app_name = "fin_mate"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("accounts/", AccountListView.as_view(), name="account-list"),
    path("accounts/create/", AccountCreateView.as_view(), name="account-create"),
    path("accounts/<int:pk>/", AccountDetailView.as_view(), name="account-detail"),
    path(
        "accounts/<int:pk>/update/", AccountUpdateView.as_view(), name="account-update"
    ),
    path(
        "accounts/<int:pk>/delete/", AccountDeleteView.as_view(), name="account-delete"
    ),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/create/", CategoryCreateView.as_view(), name="category-create"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path(
        "categories/<int:pk>/update/",
        CategoryUpdateView.as_view(),
        name="category-update",
    ),
    path(
        "categories/<int:pk>/delete/",
        CategoryDeleteView.as_view(),
        name="category-delete",
    ),
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path(
        "transactions/create/",
        TransactionCreateView.as_view(),
        name="transaction-create",
    ),
    path(
        "transactions/<int:pk>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    path(
        "transactions/<int:pk>/update/",
        TransactionUpdateView.as_view(),
        name="transaction-update",
    ),
    path(
        "transactions/<int:pk>/delete/",
        TransactionDeleteView.as_view(),
        name="transaction-delete",
    ),
    path("tags/", TagListView.as_view(), name="tag-list"),
    path("tags/create/", TagCreateView.as_view(), name="tag-create"),
    path("tags/<int:pk>/", TagDetailView.as_view(), name="tag-detail"),
    path("tags/<int:pk>/update/", TagUpdateView.as_view(), name="tag-update"),
    path("tags/<int:pk>/delete/", TagDeleteView.as_view(), name="tag-delete"),
    path("budgets/", BudgetListView.as_view(), name="budget-list"),
    path("budgets/create/", BudgetCreateView.as_view(), name="budget-create"),
    path("budgets/<int:pk>/", BudgetDetailView.as_view(), name="budget-detail"),
    path("budgets/<int:pk>/update/", BudgetUpdateView.as_view(), name="budget-update"),
    path("budgets/<int:pk>/delete/", BudgetDeleteView.as_view(), name="budget-delete"),
    path("budgets/copy/", BudgetCopyView.as_view(), name="budget-copy"),
]

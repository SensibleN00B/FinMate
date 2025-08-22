from django.urls import path

from fin_mate.views import DashboardView

app_name = "fin_mate"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
]

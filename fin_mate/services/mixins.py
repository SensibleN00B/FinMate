from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError


class UserOwnedQuerysetMixin(LoginRequiredMixin):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class OwnedCreateMixin:
    success_message = "Created ✅"

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            resp = super().form_valid(form)
        except IntegrityError as e:
            form.add_error(None, "Already exists.")
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return resp


class OwnedUpdateMixin:
    success_message = "Updated ✍️"

    def form_valid(self, form):
        try:
            resp = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Already exists.")
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return resp


class OwnedDeleteMixin:
    success_message = "Deleted 🗑️"

    def delete(self, request, *a, **kw):
        messages.success(self.request, self.success_message)
        return super().delete(request, *a, **kw)

from django.contrib import admin

from .models import Tag, Transaction, TransactionTag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "color")
    list_filter = ("user",)
    search_fields = ("name",)


class TransactionTagInline(admin.TabularInline):
    model = TransactionTag
    extra = 0
    autocomplete_fields = ("tag",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "account_id", "account", "category", "type", "amount", "date")
    list_filter = ("account__user", "type", "category")
    inlines = [TransactionTagInline]

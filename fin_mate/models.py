from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(
        max_length=63,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="categories",
        on_delete=models.CASCADE
    )
    icon = models.CharField(
        max_length=63,
        blank=True,
        help_text="Optional: name of an icon class",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="uniq_category_name_per_user",
            )
        ]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

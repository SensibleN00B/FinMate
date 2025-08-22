from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase

from fin_mate.models import Category
from fin_mate.signals import create_default_categories

DEFAULT_CATEGORIES = ["Food", "Entertainment", "Transport", "Utilities"]


class CreateDefaultCategoriesSignalTest(TestCase):

    def setUp(self):
        self.User = get_user_model()

    def test_create_default_categories_signal_creates_categories(self):
        user = self.User.objects.create_user(username="testuser", password="password")

        self.assertEqual(
            Category.objects.filter(user=user).count(), len(DEFAULT_CATEGORIES)
        )
        for category in DEFAULT_CATEGORIES:
            self.assertTrue(Category.objects.filter(user=user, name=category).exists())

    def test_create_default_categories_signal_not_triggered_on_update(self):
        user = self.User.objects.create_user(username="testuser", password="password")
        user.username = "updateduser"
        user.save()

        self.assertEqual(
            Category.objects.filter(user=user).count(), len(DEFAULT_CATEGORIES)
        )

    def test_create_default_categories_signal_handles_transaction_atomicity(self):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                self.User.objects.create_user(
                    username="testuser", password="password", email=None
                )

        self.assertEqual(Category.objects.count(), 0)

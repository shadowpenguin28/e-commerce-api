from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import uuid

User = get_user_model()


class Category(models.Model):
    """
    Product categories (Electronics, Clothing, Books, etc.)
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., 'Electronics', 'Clothing')",
    )
    description = models.TextField(
        blank=True, null=True, help_text="Optional category description"
    )

    # SEO and display
    slug = models.SlugField(
        unique=True, help_text="URL-friendly version of category name"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "inventory_category"
        verbose_name_plural = "Categories"
        ordering = ["name"]


class Item(models.Model):
    """
    Main product/item model
    Contains all product information
    """

    # Basic product info
    name = models.CharField(max_length=200, help_text="Product name")

    description = models.TextField(help_text="Detailed product description")

    # Categorization
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Product category",
    )

    # Pricing and inventory
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Product price in currency units",
    )

    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Available stock quantity",
    )

    # Product identification
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="Stock Keeping Unit - unique product identifier",
    )

    # Media
    image = models.ImageField(
        upload_to="items/", blank=True, null=True, help_text="Product image"
    )

    # Status
    is_active = models.BooleanField(
        default=True, help_text="Is product available for purchase"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When product was first created"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When product was last modified"
    )

    restocked_at = models.DateTimeField(
        auto_now=True, help_text="When product was last restocked"
    )

    def __str__(self):
        return f"{self.name} - ${self.price}"

    @property
    def is_in_stock(self):
        """Check if item is in stock"""
        return self.quantity > 0 and self.is_active

    @property
    def is_low_stock(self, threshold=5):
        """Check if item is running low on stock"""
        return self.quantity <= threshold and self.quantity > 0

    def save(self, *args, **kwargs):
        """Override save to generate SKU if not provided"""
        if not self.sku:
            self.sku = f"ITEM-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        db_table = "inventory_item"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["price"]),
            models.Index(fields=["created_at"]),
        ]


class StockMovement(models.Model):
    """
    Tracking of stock changes
    """

    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="stock_movements"
    )

    quantity_change = models.IntegerField(
        help_text="Positive for additions (restock), negative for reductions (sale)"
    )

    reason = models.CharField(
        max_length=50, help_text="Why stock changed: 'restock', 'sale', 'adjustment'"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sign = "+" if self.quantity_change >= 0 else ""
        return f"{self.item.name}: {sign}{self.quantity_change} ({self.reason})"

    class Meta:
        db_table = "inventory_stock_movement"
        ordering = ["-created_at"]

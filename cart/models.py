from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class Cart(models.Model):
    """
    Shopping cart for each user
    One cart per user (can be extended to support multiple carts)
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="cart", help_text="Cart owner"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When cart was first created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When cart was last modified"
    )

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_items(self):
        """Total number of items in cart"""
        return self.cart_items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def total_price(self):
        """Total price of all items in cart"""
        total = self.cart_items.aggregate(
            total=models.Sum(
                models.F("quantity") * models.F("item__price"),
                output_field=models.DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]
        return total or Decimal("0.00")

    @property
    def is_empty(self):
        """Check if cart is empty"""
        return self.cart_items.count() == 0

    def clear(self):
        """Remove all items from cart"""
        self.cart_items.all().delete()

    def add_item(self, item, quantity=1):
        """
        Add item to cart or update quantity if item already exists
        """
        cart_item, created = CartItem.objects.get_or_create(
            cart=self, item=item, defaults={"quantity": quantity}
        )

        if not created:
            # Item already in cart, update quantity
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    def remove_item(self, item):
        """Remove item from cart completely"""
        try:
            cart_item = self.cart_items.get(item=item)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            return False

    def update_item_quantity(self, item, quantity):
        """Update specific item quantity in cart"""
        try:
            cart_item = self.cart_items.get(item=item)
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            return True
        except CartItem.DoesNotExist:
            return False

    class Meta:
        db_table = "cart_cart"


class CartItem(models.Model):
    """
    Individual items in a cart
    Links cart to inventory items with quantities
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")

    item = models.ForeignKey(
        "inventory.Item",
        on_delete=models.CASCADE,
        help_text="Reference to inventory item",
    )

    quantity = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Quantity of item in cart"
    )

    added_at = models.DateTimeField(
        auto_now_add=True, help_text="When item was added to cart"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When cart item was last updated"
    )

    def __str__(self):
        return f"{self.item.name} x{self.quantity} in {self.cart.user.username}'s cart"

    @property
    def total_price(self):
        """Total price for this cart item"""
        return self.quantity * self.item.price

    @property
    def is_available(self):
        """Check if requested quantity is available in stock"""
        return self.item.is_active and self.item.quantity >= self.quantity

    def clean(self):
        """Validate cart item before saving"""
        from django.core.exceptions import ValidationError

        if not self.item.is_active:
            raise ValidationError("Cannot add inactive item to cart")

        if self.quantity > self.item.quantity:
            raise ValidationError(f"Only {self.item.quantity} items available in stock")

    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.full_clean()  # This calls clean() method
        super().save(*args, **kwargs)

    class Meta:
        db_table = "cart_cartitem"
        # Ensure one cart item per item per cart
        unique_together = ["cart", "item"]
        ordering = ["-added_at"]

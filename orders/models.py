# orders/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import uuid
from decimal import Decimal

User = get_user_model()

class Order(models.Model):
    """
    Main order model
    Contains order information and delivery details
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Order identification
    order_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Unique order identifier (e.g., ORD-ABC123)"
    )
    
    # Customer info
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="Customer who placed the order"
    )
    
    # Order status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Financial info
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Sum of all order items"
    )
    
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Tax amount"
    )
    
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Shipping cost"
    )
    
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Final total amount"
    )
    
    # Delivery information
    shipping_address = models.TextField(
        help_text="Full shipping address",
        max_length=512,
    )
    
    phone_number = models.CharField(
        max_length=15,
        help_text="Contact number for delivery"
    )
    
    # Optional delivery instructions
    delivery_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Special delivery instructions",
        max_length=512,
    )  
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When order was placed"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When order was last updated"
    )
    # Optional: Expected and actual delivery dates
    expected_delivery = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Expected delivery date"
    )
    
    delivered_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Actual delivery date"
    )
    
    def __str__(self):
        return f"Order {self.order_id} - {self.customer.username}"
    
    def save(self, *args, **kwargs):
        """Generate order ID if not provided"""
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def item_count(self):
        """Total number of items in order"""
        return self.order_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    def calculate_totals(self):
        """Recalculate order totals based on order items"""
        subtotal = self.order_items.aggregate(
            total=models.Sum(
                models.F('quantity') * models.F('price'),
                output_field=models.DecimalField(max_digits=10, decimal_places=2)
            )
        )['total'] or Decimal('0.00')
        
        self.subtotal = subtotal
        # You can add tax calculation logic here
        # self.tax_amount = subtotal * Decimal('0.10')  # 10% tax
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
    
    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]


class OrderItem(models.Model):
    """
    Individual items within an order
    Links orders to inventory items with quantities and prices
    """
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    
    # Product info (stored to preserve historical data)
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.CASCADE,
        help_text="Reference to inventory item"
    )
    
    # Historical data (in case item details change after order)
    item_name = models.CharField(
        max_length=200,
        help_text="Item name at time of order"
    )
    
    item_sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Item SKU at time of order"
    )
    
    # Order-specific data
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity ordered"
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per item at time of order"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.item_name} x{self.quantity} - Order {self.order.order_id}"
    
    @property
    def total_price(self):
        """Total price for this order item"""
        return self.quantity * self.price
    
    def save(self, *args, **kwargs):
        """Auto-populate item details from inventory"""
        if not self.item_name and self.item:
            self.item_name = self.item.name
            self.item_sku = self.item.sku
            self.price = self.item.price
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'orders_orderitem'
        # Prevent duplicate items in same order
        unique_together = ['order', 'item']


class OrderStatusHistory(models.Model):
    """
    Track order status changes for auditing
    """
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    
    from_status = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    
    to_status = models.CharField(max_length=20)
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for status change"
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order {self.order.order_id}: {self.from_status} → {self.to_status}"
    
    class Meta:
        db_table = 'orders_status_history'
        ordering = ['-created_at']
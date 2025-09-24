from rest_framework import serializers
from django.utils.text import slugify
from .models import Category, Item, StockMovement
from orders.models import Order, OrderItem

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'slug', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Auto-generate slug from name"""
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class ItemListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing items (minimal data)
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'sku', 'category_name', 'price', 
            'quantity', 'is_active', 'is_in_stock', 'is_low_stock',
            'created_at', 'restocked_at'
        ]


class ItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed item view (full data)
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'description', 'sku', 'category', 'category_name',
            'price', 'quantity', 'image', 'is_active', 'is_in_stock', 
            'is_low_stock', 'total_value', 'created_at', 'updated_at', 'restocked_at'
        ]
        read_only_fields = ['sku', 'created_at', 'updated_at', 'restocked_at']
    
    def get_total_value(self, obj):
        """Calculate total inventory value for this item"""
        return obj.price * obj.quantity


class ItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new items
    """
    class Meta:
        model = Item
        fields = [
            'name', 'description', 'category', 'price', 
            'quantity', 'image', 'is_active'
        ]
    
    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value
    
    def validate_quantity(self, value):
        """Validate quantity is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative")
        return value
    
    def create(self, validated_data):
        """Create item and log stock movement"""
        item = super().create(validated_data)
        
        # Log initial stock as a stock movement
        if item.quantity > 0:
            StockMovement.objects.create(
                item=item,
                quantity_change=item.quantity,
                reason="initial_stock"
            )
        
        return item


class ItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating items (excluding quantity - use restock for that)
    """
    class Meta:
        model = Item
        fields = [
            'name', 'description', 'category', 'price', 
            'image', 'is_active'
        ]
        # Quantity is excluded - use restock endpoint instead
    
    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value


class RestockSerializer(serializers.Serializer):
    """
    Serializer for restocking items
    """
    quantity_to_add = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=50, default="restock")
    
    def validate_quantity_to_add(self, value):
        """Validate quantity to add is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity to add must be greater than 0")
        return value
    
    def update(self, instance, validated_data):
        """Update item quantity and log stock movement"""
        quantity_to_add = validated_data['quantity_to_add']
        reason = validated_data.get('reason', 'restock')
        
        # Update item quantity
        old_quantity = instance.quantity
        instance.quantity += quantity_to_add
        instance.save(update_fields=['quantity', 'restocked_at'])
        
        # Log stock movement
        StockMovement.objects.create(
            item=instance,
            quantity_change=quantity_to_add,
            reason=reason
        )
        
        return instance


class StockMovementSerializer(serializers.ModelSerializer):
    """
    Serializer for stock movements
    """
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'item', 'item_name', 'quantity_change', 
            'reason', 'created_at'
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items in inventory management
    """
    item_name = serializers.CharField(read_only=True)
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'item_name', 'item_sku', 'quantity', 'price', 'total_price']


class OrderManagementSerializer(serializers.ModelSerializer):
    """
    Serializer for order management by shopkeepers
    """
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    item_count = serializers.ReadOnlyField()
    order_items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'customer', 'customer_name', 'customer_email', 
            'customer_phone', 'status', 'item_count', 'subtotal', 'tax_amount', 
            'shipping_cost', 'total_amount', 'shipping_address', 'phone_number',
            'delivery_instructions', 'created_at', 'updated_at', 'order_items'
        ]
        read_only_fields = [
            'order_id', 'customer', 'subtotal', 'tax_amount', 
            'total_amount', 'created_at', 'updated_at'
        ]


class RevenueSerializer(serializers.Serializer):
    """
    Serializer for revenue data
    """
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue_by_status = serializers.DictField()
    revenue_by_month = serializers.ListField(required=False)
    top_selling_items = serializers.ListField(required=False)
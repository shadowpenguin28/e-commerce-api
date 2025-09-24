from rest_framework import serializers
from .models import Order, OrderItem
from inventory.models import Item

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items
    """
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'item', 'item_name', 'item_sku', 
            'quantity', 'price', 'total_price'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """
    Serializer for order list (minimal data)
    """
    item_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'item_count',
            'total_amount', 'created_at'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed order view
    """
    order_items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'item_count',
            'subtotal', 'tax_amount', 'shipping_cost', 'total_amount',
            'shipping_address', 'phone_number', 'delivery_instructions',
            'created_at', 'updated_at', 'expected_delivery', 'delivered_at',
            'order_items'
        ]


class CreateOrderSerializer(serializers.Serializer):
    """
    Serializer for creating a direct order (not from cart)
    """
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        min_length=1
    )
    shipping_address = serializers.CharField(max_length=500)
    phone_number = serializers.CharField(max_length=15)
    delivery_instructions = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True
    )
    
    def validate_items(self, value):
        """Validate items format and availability"""
        validated_items = []
        
        for item_data in value:
            # Validate required fields
            if 'item_id' not in item_data or 'quantity' not in item_data:
                raise serializers.ValidationError(
                    "Each item must have 'item_id' and 'quantity'"
                )
            
            try:
                item_id = int(item_data['item_id'])
                quantity = int(item_data['quantity'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "item_id and quantity must be integers"
                )
            
            if quantity <= 0:
                raise serializers.ValidationError(
                    "Quantity must be greater than 0"
                )
            
            # Validate item exists and is available
            try:
                item = Item.objects.get(id=item_id)
                if not item.is_active:
                    raise serializers.ValidationError(
                        f"Item '{item.name}' is not available"
                    )
                if item.quantity < quantity:
                    raise serializers.ValidationError(
                        f"Only {item.quantity} of '{item.name}' available in stock"
                    )
                
                validated_items.append({
                    'item': item,
                    'quantity': quantity
                })
                
            except Item.DoesNotExist:
                raise serializers.ValidationError(
                    f"Item with ID {item_id} not found"
                )
        
        return validated_items
    
    def validate_shipping_address(self, value):
        """Validate shipping address"""
        if not value.strip():
            raise serializers.ValidationError("Shipping address is required")
        return value.strip()
    
    def validate_phone_number(self, value):
        """Basic phone number validation"""
        import re
        phone_pattern = re.compile(r'^[\+]?[1-9][\d]{0,15}$')
        if not phone_pattern.match(value.replace('-', '').replace(' ', '')):
            raise serializers.ValidationError("Invalid phone number format")
        return value
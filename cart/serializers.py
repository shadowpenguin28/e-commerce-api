from rest_framework import serializers
from decimal import Decimal
from .models import Cart, CartItem
from inventory.models import Item


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for cart items
    """

    item_name = serializers.CharField(source="item.name", read_only=True)
    item_price = serializers.DecimalField(
        source="item.price", max_digits=10, decimal_places=2, read_only=True
    )
    item_image = serializers.SerializerMethodField()
    total_price = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "item",
            "item_name",
            "item_price",
            "item_image",
            "quantity",
            "total_price",
            "is_available",
            "added_at",
        ]
        read_only_fields = ["id", "added_at"]

    def get_item_image(self, obj):
        """Get item image URL"""
        if obj.item.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.item.image.url)
            return obj.item.image.url
        return None


class AddToCartSerializer(serializers.Serializer):
    """
    Serializer for adding items to cart
    """

    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_item_id(self, value):
        """Validate item exists and is available"""
        try:
            item = Item.objects.get(id=value)
            if not item.is_active:
                raise serializers.ValidationError("Item is not available")
            if item.quantity == 0:
                raise serializers.ValidationError("Item is out of stock")
            return value
        except Item.DoesNotExist:
            raise serializers.ValidationError("Item not found")

    def validate(self, attrs):
        """Validate quantity against available stock"""
        item = Item.objects.get(id=attrs["item_id"])
        if attrs["quantity"] > item.quantity:
            raise serializers.ValidationError(
                f"Only {item.quantity} items available in stock"
            )
        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """
    Serializer for updating cart item quantity
    """

    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        """Validate quantity against available stock"""
        cart_item = self.context.get("cart_item")
        if cart_item and value > cart_item.item.quantity:
            raise serializers.ValidationError(
                f"Only {cart_item.item.quantity} items available in stock"
            )
        return value


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for complete cart information
    """

    cart_items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    is_empty = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "total_items",
            "total_price",
            "is_empty",
            "cart_items",
            "created_at",
            "updated_at",
        ]


class CheckoutSerializer(serializers.Serializer):
    """
    Serializer for cart checkout
    """

    shipping_address = serializers.CharField(max_length=500)
    phone_number = serializers.CharField(max_length=15)
    delivery_instructions = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    def validate_shipping_address(self, value):
        """Validate shipping address is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Shipping address is required")
        return value.strip()

    def validate_phone_number(self, value):
        """Basic phone number validation"""
        import re

        phone_pattern = re.compile(r"^[\+]?[1-9][\d]{0,15}$")
        if not phone_pattern.match(value.replace("-", "").replace(" ", "")):
            raise serializers.ValidationError("Invalid phone number format")
        return value

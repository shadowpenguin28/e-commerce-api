from rest_framework import serializers
from inventory.models import Category, Item

class ShopCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for public category display
    """
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'slug', 'item_count']
    
    def get_item_count(self, obj):
        """Get count of active items in this category"""
        return obj.items.filter(is_active=True, quantity__gt=0).count()

class ShopItemListSerializer(serializers.ModelSerializer):
    """
    Serializer for public item listing (minimal data for performance)
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'price', 'category_name', 'category_slug',
            'is_in_stock', 'image_url', 'created_at'
        ]
    
    def get_image_url(self, obj):
        """Get full image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ShopItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed item view (for individual product pages)
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'description', 'price', 'category_name', 
            'category_slug', 'is_in_stock', 'is_low_stock', 'stock_status',
            'image_url', 'created_at'
        ]
        # Exclude sensitive fields like quantity, sku, etc.
    
    def get_image_url(self, obj):
        """Get full image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_stock_status(self, obj):
        """Get user-friendly stock status"""
        if not obj.is_active:
            return "Unavailable"
        elif obj.quantity == 0:
            return "Out of Stock"
        elif obj.quantity <= 5:
            return "Limited Stock"
        else:
            return "In Stock"


class ShopSearchResultSerializer(serializers.ModelSerializer):
    """
    Serializer for search results with highlighting
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'description', 'price', 'category_name',
            'is_in_stock', 'image_url', 'match_score'
        ]
    
    def get_image_url(self, obj):
        """Get full image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_match_score(self, obj):
        """Calculate relevance score for search results"""
        search_term = self.context.get('search_term', '').lower()
        if not search_term:
            return 0
        
        score = 0
        name_lower = obj.name.lower()
        desc_lower = obj.description.lower()
        
        # Higher score for exact name matches
        if search_term in name_lower:
            score += 10
        
        # Medium score for description matches
        if search_term in desc_lower:
            score += 5
        
        # Bonus for name starting with search term
        if name_lower.startswith(search_term):
            score += 15
        
        return score


class PaginationSerializer(serializers.Serializer):
    """
    Serializer for pagination metadata
    """
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    current_page = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    page_size = serializers.IntegerField()


class ShopListResponseSerializer(serializers.Serializer):
    """
    Serializer for shop list API response
    """
    success = serializers.BooleanField()
    pagination = PaginationSerializer()
    filters_applied = serializers.DictField()
    items = ShopItemListSerializer(many=True)
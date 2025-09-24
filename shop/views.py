from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal
import logging

from inventory.models import Category, Item
from .serializers import (
    ShopCategorySerializer, ShopItemListSerializer, 
    ShopItemDetailSerializer, ShopSearchResultSerializer
)

logger = logging.getLogger(__name__)


class ShopPagination(PageNumberPagination):
    """
    Custom pagination for shop items
    """
    page_size = 12  # Default items per page
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'pagination': {
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.page_size
            },
            'items': data
        })


@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint
def shop_item_list(request):
    """
    Public item listing with filtering, search, and pagination
    GET /shop/list
    GET /shop/list?category=electronics
    GET /shop/list?price=100-500
    GET /shop/list?search=laptop
    """
    try:
        # Start with active items that are in stock
        items = Item.objects.select_related('category').filter(
            is_active=True,
            quantity__gt=0
        )
        
        # Track applied filters for response
        filters_applied = {}
        
        # Category filter
        category_param = request.GET.get('category')
        if category_param:
            # Support both category slug and ID
            if category_param.isdigit():
                items = items.filter(category__id=category_param)
                category_obj = Category.objects.filter(id=category_param).first()
                filters_applied['category'] = category_obj.name if category_obj else category_param
            else:
                items = items.filter(category__slug=category_param)
                category_obj = Category.objects.filter(slug=category_param).first()
                filters_applied['category'] = category_obj.name if category_obj else category_param
        
        # Price range filter
        price_param = request.GET.get('price')
        if price_param:
            try:
                if '-' in price_param:
                    min_price, max_price = price_param.split('-')
                    min_price = Decimal(min_price.strip())
                    max_price = Decimal(max_price.strip())
                    items = items.filter(price__gte=min_price, price__lte=max_price)
                    filters_applied['price_range'] = f"${min_price} - ${max_price}"
                else:
                    # Single price value (less than or equal to)
                    max_price = Decimal(price_param.strip())
                    items = items.filter(price__lte=max_price)
                    filters_applied['max_price'] = f"≤ ${max_price}"
            except (ValueError, TypeError):
                logger.warning(f"Invalid price format: {price_param}")
        
        # Search functionality
        search_param = request.GET.get('search')
        if search_param:
            search_query = Q(name__icontains=search_param) | Q(description__icontains=search_param)
            items = items.filter(search_query)
            filters_applied['search'] = search_param
        
        # Sorting
        sort_param = request.GET.get('sort', 'created_at')
        valid_sort_options = {
            'name': 'name',
            'price_asc': 'price',
            'price_desc': '-price',
            'newest': '-created_at',
            'oldest': 'created_at'
        }
        
        sort_field = valid_sort_options.get(sort_param, '-created_at')
        items = items.order_by(sort_field)
        
        if sort_param in valid_sort_options:
            filters_applied['sort'] = sort_param
        
        # Handle search with scoring (if search parameter exists)
        if search_param:
            # Use search-specific serializer with relevance scoring
            paginator = ShopPagination()
            paginated_items = paginator.paginate_queryset(items, request)
            
            serializer = ShopSearchResultSerializer(
                paginated_items, 
                many=True, 
                context={'request': request, 'search_term': search_param}
            )
            
            # Sort by relevance score
            serialized_data = sorted(
                serializer.data, 
                key=lambda x: x.get('match_score', 0), 
                reverse=True
            )
            
            return paginator.get_paginated_response(serialized_data)
        
        else:
            # Regular listing with pagination
            paginator = ShopPagination()
            paginated_items = paginator.paginate_queryset(items, request)
            
            serializer = ShopItemListSerializer(
                paginated_items, 
                many=True, 
                context={'request': request}
            )
            
            response = paginator.get_paginated_response(serializer.data)
            response.data['filters_applied'] = filters_applied
            return response
    
    except Exception as e:
        logger.error(f"Error in shop item list: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve items',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def shop_item_detail(request, item_id):
    """
    Get detailed information about a specific item
    GET /shop/item/<id>
    """
    try:
        item = get_object_or_404(
            Item.objects.select_related('category'),
            id=item_id,
            is_active=True
        )
        
        serializer = ShopItemDetailSerializer(item, context={'request': request})
        
        return Response({
            'success': True,
            'item': serializer.data
        })
    
    except Item.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Item not found or not available'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error retrieving item detail: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve item details',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def shop_categories(request):
    """
    Get all available categories with item counts
    GET /shop/categories
    """
    try:
        # Only show categories that have active items
        categories = Category.objects.filter(
            items__is_active=True,
            items__quantity__gt=0
        ).distinct().order_by('name')
        
        serializer = ShopCategorySerializer(categories, many=True)
        
        return Response({
            'success': True,
            'categories': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Error retrieving categories: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve categories',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def shop_search_suggestions(request):
    """
    Get search suggestions based on partial input
    GET /shop/search-suggestions?q=lap
    """
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return Response({
                'success': True,
                'suggestions': []
            })
        
        # Get item name suggestions
        items = Item.objects.filter(
            is_active=True,
            quantity__gt=0,
            name__icontains=query
        ).values_list('name', flat=True)[:10]
        
        # Get category suggestions
        categories = Category.objects.filter(
            name__icontains=query,
            items__is_active=True,
            items__quantity__gt=0
        ).distinct().values_list('name', flat=True)[:5]
        
        suggestions = list(set(list(items) + list(categories)))[:10]
        
        return Response({
            'success': True,
            'suggestions': sorted(suggestions)
        })
    
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to get suggestions',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def shop_featured_items(request):
    """
    Get featured/recommended items
    GET /shop/featured
    """
    try:
        # Get latest items (you can customize this logic)
        featured_items = Item.objects.select_related('category').filter(
            is_active=True,
            quantity__gt=0
        ).order_by('-created_at')[:8]
        
        serializer = ShopItemListSerializer(
            featured_items, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'success': True,
            'featured_items': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Error retrieving featured items: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve featured items',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def shop_price_range(request):
    """
    Get available price range for filtering
    GET /shop/price-range
    """
    try:
        from django.db.models import Min, Max
        
        price_range = Item.objects.filter(
            is_active=True,
            quantity__gt=0
        ).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        
        return Response({
            'success': True,
            'price_range': {
                'min_price': float(price_range['min_price'] or 0),
                'max_price': float(price_range['max_price'] or 0)
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting price range: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to get price range',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
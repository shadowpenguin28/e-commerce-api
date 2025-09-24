from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from decimal import Decimal
import logging

from authentication.permissions import IsShopkeeper
from .models import Category, Item, StockMovement
from orders.models import Order, OrderItem
from .serializers import (
    CategorySerializer, ItemListSerializer, ItemDetailSerializer,
    ItemCreateSerializer, ItemUpdateSerializer, RestockSerializer,
    StockMovementSerializer, OrderManagementSerializer, RevenueSerializer
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def list_items(request):
    """
    List all items for inventory management
    GET /inventory/list
    """
    try:
        items = Item.objects.select_related('category').all()
        
        # Optional filtering
        category = request.GET.get('category')
        if category:
            items = items.filter(category__slug=category)
        
        active_only = request.GET.get('active_only', '').lower() == 'true'
        if active_only:
            items = items.filter(is_active=True)
        
        low_stock_only = request.GET.get('low_stock_only', '').lower() == 'true'
        if low_stock_only:
            items = items.filter(quantity__lte=5, quantity__gt=0)
        
        out_of_stock_only = request.GET.get('out_of_stock_only', '').lower() == 'true'
        if out_of_stock_only:
            items = items.filter(quantity=0)
        
        serializer = ItemListSerializer(items, many=True)
        
        return Response({
            'success': True,
            'count': items.count(),
            'items': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Error listing items: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve items',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsShopkeeper])
def create_category(request):
    """
    Create a new cateogry
    POST /inventory/category/new/
    """

    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        try:
            category = serializer.save()
            logger.info(f"New category created: {category.name} by {request.user.username}")

            return Response({
                'success': True,
                'message': 'Category created successfully'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error in creating category: {e}")
            return Response({
                'success': False,
                'message': 'Failed to create category' 
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def create_item(request):
    """
    Create a new item
    POST /inventory/new
    """
    serializer = ItemCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            item = serializer.save()
            
            # Return detailed item data
            detail_serializer = ItemDetailSerializer(item)
            
            logger.info(f"New item created: {item.name} by {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Item created successfully',
                'item': detail_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error creating item: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to create item',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def update_item(request, item_id):
    """
    Get or update an item
    GET/PUT /inventory/update/<id>
    """
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'GET':
        # Return detailed item information
        serializer = ItemDetailSerializer(item)
        return Response({
            'success': True,
            'item': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = ItemUpdateSerializer(item, data=request.data)
        
        if serializer.is_valid():
            try:
                updated_item = serializer.save()
                
                # Return updated item data
                detail_serializer = ItemDetailSerializer(updated_item)
                
                logger.info(f"Item updated: {updated_item.name} by {request.user.username}")
                
                return Response({
                    'success': True,
                    'message': 'Item updated successfully',
                    'item': detail_serializer.data
                })
            
            except Exception as e:
                logger.error(f"Error updating item: {str(e)}")
                return Response({
                    'success': False,
                    'message': 'Failed to update item',
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def restock_item(request, item_id):
    """
    Restock an item (add quantity)
    PATCH /inventory/restock/<id>
    """
    item = get_object_or_404(Item, id=item_id)
    
    serializer = RestockSerializer(item, data=request.data)
    
    if serializer.is_valid():
        try:
            updated_item = serializer.save()
            
            # Return updated item data
            detail_serializer = ItemDetailSerializer(updated_item)
            
            logger.info(f"Item restocked: {updated_item.name} (+{request.data.get('quantity_to_add')}) by {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Item restocked successfully',
                'item': detail_serializer.data
            })
        
        except Exception as e:
            logger.error(f"Error restocking item: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to restock item',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def view_orders(request):
    """
    View all orders for inventory management
    GET /inventory/orders
    """
    try:
        orders = Order.objects.select_related('customer').prefetch_related('order_items__item').all()
        
        # Optional filtering
        status_filter = request.GET.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        customer_search = request.GET.get('customer')
        if customer_search:
            orders = orders.filter(
                Q(customer__username__icontains=customer_search) |
                Q(customer__first_name__icontains=customer_search) |
                Q(customer__last_name__icontains=customer_search) |
                Q(customer__email__icontains=customer_search)
            )
        
        # Ordering
        orders = orders.order_by('-created_at')
        
        serializer = OrderManagementSerializer(orders, many=True)
        
        # Summary stats
        total_orders = orders.count()
        total_revenue = orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        return Response({
            'success': True,
            'summary': {
                'total_orders': total_orders,
                'total_revenue': total_revenue
            },
            'orders': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Error retrieving orders: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve orders',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def revenue_report(request):
    """
    Get revenue analytics
    GET /inventory/revenue
    """
    try:
        # Basic revenue metrics
        orders = Order.objects.exclude(status='cancelled')
        
        total_revenue = orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        total_orders = orders.count()
        
        average_order_value = orders.aggregate(
            avg=Avg('total_amount')
        )['avg'] or Decimal('0.00')
        
        # Revenue by order status
        revenue_by_status = {}
        for status_choice in Order.STATUS_CHOICES:
            status_code = status_choice[0]
            status_revenue = orders.filter(status=status_code).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00')
            if status_revenue > 0:
                revenue_by_status[status_code] = float(status_revenue)
        
        # Monthly revenue (last 12 months)
        monthly_revenue = orders.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('-month')[:12]
        
        revenue_by_month = [
            {
                'month': item['month'].strftime('%Y-%m') if item['month'] else '',
                'revenue': float(item['revenue'] or 0),
                'order_count': item['order_count']
            }
            for item in monthly_revenue
        ]
        
        # Top selling items
        top_items = OrderItem.objects.values(
            'item__name', 'item__id'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('quantity') * Sum('price') / Sum('quantity')  # Weighted average price
        ).order_by('-total_sold')[:10]
        
        top_selling_items = [
            {
                'item_id': item['item__id'],
                'item_name': item['item__name'],
                'total_sold': item['total_sold'],
                'total_revenue': float(item['total_revenue'] or 0)
            }
            for item in top_items
        ]
        
        # Prepare response data
        revenue_data = {
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'average_order_value': float(average_order_value),
            'revenue_by_status': revenue_by_status,
            'revenue_by_month': revenue_by_month,
            'top_selling_items': top_selling_items
        }
        
        # Validate with serializer
        serializer = RevenueSerializer(data=revenue_data)
        if serializer.is_valid():
            return Response({
                'success': True,
                'revenue_data': serializer.validated_data
            })
        else:
            # Return data anyway, but log validation errors
            logger.warning(f"Revenue data validation errors: {serializer.errors}")
            return Response({
                'success': True,
                'revenue_data': revenue_data
            })
    
    except Exception as e:
        logger.error(f"Error generating revenue report: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to generate revenue report',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Helper endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def list_categories(request):
    """
    List all categories
    GET /inventory/categories
    """
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response({
        'success': True,
        'categories': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShopkeeper])
def stock_movements(request, item_id):
    """
    Get stock movement history for an item
    GET /inventory/stock-movements/<item_id>
    """
    item = get_object_or_404(Item, id=item_id)
    movements = StockMovement.objects.filter(item=item).order_by('-created_at')
    serializer = StockMovementSerializer(movements, many=True)
    
    return Response({
        'success': True,
        'item_name': item.name,
        'current_stock': item.quantity,
        'stock_movements': serializer.data
    })
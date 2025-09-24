from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

from .models import Order, OrderItem
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, CreateOrderSerializer
)
from inventory.models import Item, StockMovement

logger = logging.getLogger(__name__)


class OrderPagination(PageNumberPagination):
    """
    Custom pagination for orders
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def past_orders(request):
    """
    Get user's past orders
    GET /orders/past
    """
    try:
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
        
        # Optional status filtering
        status_filter = request.GET.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Pagination
        paginator = OrderPagination()
        paginated_orders = paginator.paginate_queryset(orders, request)
        
        serializer = OrderListSerializer(paginated_orders, many=True)
        
        return paginator.get_paginated_response({
            'success': True,
            'orders': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Error retrieving past orders: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve orders',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """
    Get detailed information about a specific order
    GET /orders/detail/<order_id>
    """
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('order_items'), 
            id=order_id,
            customer=request.user
        )
        
        serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'order': serializer.data
        })
    
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error retrieving order detail: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve order details',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Create a new order directly (not from cart)
    POST /orders/new
    """
    serializer = CreateOrderSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                validated_items = serializer.validated_data['items']
                
                # Create order
                order = Order.objects.create(
                    customer=request.user,
                    shipping_address=serializer.validated_data['shipping_address'],
                    phone_number=serializer.validated_data['phone_number'],
                    delivery_instructions=serializer.validated_data.get('delivery_instructions', ''),
                    status='pending'
                )
                
                # Create order items and update stock
                for item_data in validated_items:
                    item = item_data['item']
                    quantity = item_data['quantity']
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        item=item,
                        item_name=item.name,
                        item_sku=item.sku,
                        quantity=quantity,
                        price=item.price
                    )
                    
                    # Update stock
                    item.quantity -= quantity
                    item.save()
                    
                    # Log stock movement
                    StockMovement.objects.create(
                        item=item,
                        quantity_change=-quantity,
                        reason="sale"
                    )
                
                # Calculate order totals
                order.calculate_totals()
                
                # Return order details
                order_serializer = OrderDetailSerializer(order)
                
                logger.info(f"Direct order created: {order.order_id} for user {request.user.username}")
                
                return Response({
                    'success': True,
                    'message': 'Order created successfully',
                    'order': order_serializer.data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to create order',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """
    Cancel an order (if it's still pending)
    POST /orders/cancel/<order_id>
    """
    try:
        order = get_object_or_404(
            Order,
            id=order_id,
            customer=request.user
        )
        
        # Check if order can be cancelled
        if order.status not in ['pending', 'processing']:
            return Response({
                'success': False,
                'message': f'Cannot cancel order with status: {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Restore stock for all items
            for order_item in order.order_items.all():
                item = order_item.item
                item.quantity += order_item.quantity
                item.save()
                
                # Log stock movement
                StockMovement.objects.create(
                    item=item,
                    quantity_change=order_item.quantity,
                    reason="order_cancelled"
                )
            
            # Update order status
            order.status = 'cancelled'
            order.save()
            
            logger.info(f"Order cancelled: {order.order_id} by user {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Order cancelled successfully',
                'order_id': order.order_id
            })
    
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to cancel order',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_status(request, order_id):
    """
    Get current status of an order
    GET /orders/status/<order_id>
    """
    try:
        order = get_object_or_404(
            Order,
            id=order_id,
            customer=request.user
        )
        
        return Response({
            'success': True,
            'order_id': order.order_id,
            'status': order.status,
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'expected_delivery': order.expected_delivery,
            'delivered_at': order.delivered_at
        })
    
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error retrieving order status: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve order status',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_summary(request):
    """
    Get user's order summary statistics
    GET /orders/summary
    """
    try:
        orders = Order.objects.filter(customer=request.user)
        
        from django.db.models import Count, Sum
        from decimal import Decimal
        
        summary = orders.aggregate(
            total_orders=Count('id'),
            total_spent=Sum('total_amount'),
        )
        
        # Count by status
        status_counts = {}
        for status_choice in Order.STATUS_CHOICES:
            status_code = status_choice[0]
            count = orders.filter(status=status_code).count()
            if count > 0:
                status_counts[status_code] = count
        
        return Response({
            'success': True,
            'summary': {
                'total_orders': summary['total_orders'] or 0,
                'total_spent': float(summary['total_spent'] or Decimal('0.00')),
                'status_breakdown': status_counts
            }
        })
    
    except Exception as e:
        logger.error(f"Error retrieving order summary: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve order summary',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
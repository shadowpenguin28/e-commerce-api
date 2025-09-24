from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
import logging

from .models import Cart, CartItem
from .serializers import (
    CartSerializer, AddToCartSerializer, UpdateCartItemSerializer, 
    CheckoutSerializer
)
from orders.models import Order, OrderItem
from orders.serializers import OrderDetailSerializer
from inventory.models import Item, StockMovement

logger = logging.getLogger(__name__)


def get_or_create_cart(user):
    """
    Get or create cart for user
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """
    Add item to cart
    POST /cart/add/
    """
    serializer = AddToCartSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                item_id = serializer.validated_data['item_id']
                quantity = serializer.validated_data['quantity']
                
                # Get or create user's cart
                cart = get_or_create_cart(request.user)
                
                # Get the item
                item = Item.objects.get(id=item_id)
                
                # Check if item already in cart
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    item=item,
                    defaults={'quantity': quantity}
                )
                
                if not created:
                    # Item already in cart, update quantity
                    new_quantity = cart_item.quantity + quantity
                    
                    # Check stock availability
                    if new_quantity > item.quantity:
                        return Response({
                            'success': False,
                            'message': f'Only {item.quantity} items available. You already have {cart_item.quantity} in your cart.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    cart_item.quantity = new_quantity
                    cart_item.save()
                    message = f"Updated quantity of {item.name} in cart"
                else:
                    message = f"Added {item.name} to cart"
                
                # Return updated cart info
                cart_serializer = CartSerializer(cart, context={'request': request})
                
                logger.info(f"Cart updated for user {request.user.username}: {message}")
                
                return Response({
                    'success': True,
                    'message': message,
                    'cart': cart_serializer.data
                }, status=status.HTTP_201_CREATED)
        
        except Item.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error adding item to cart: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to add item to cart',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_info(request):
    """
    Get current cart information
    GET /cart/info/
    """
    try:
        cart = get_or_create_cart(request.user)
        serializer = CartSerializer(cart, context={'request': request})
        
        return Response({
            'success': True,
            'cart': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Error retrieving cart info: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to retrieve cart information',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    """
    Remove item from cart
    DELETE /cart/remove/<item_id>/
    """
    try:
        cart = get_or_create_cart(request.user)
        
        # Find cart item
        cart_item = get_object_or_404(
            CartItem, 
            cart=cart, 
            item_id=item_id
        )
        
        item_name = cart_item.item.name
        cart_item.delete()
        
        # Return updated cart info
        cart_serializer = CartSerializer(cart, context={'request': request})
        
        logger.info(f"Removed {item_name} from cart for user {request.user.username}")
        
        return Response({
            'success': True,
            'message': f'Removed {item_name} from cart',
            'cart': cart_serializer.data
        })
    
    except CartItem.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Item not found in cart'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error removing item from cart: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to remove item from cart',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    """
    Update cart item quantity
    PUT /cart/update/<item_id>/
    """
    try:
        cart = get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, cart=cart, item_id=item_id)
        
        serializer = UpdateCartItemSerializer(
            data=request.data, 
            context={'cart_item': cart_item}
        )
        
        if serializer.is_valid():
            cart_item.quantity = serializer.validated_data['quantity']
            cart_item.save()
            
            # Return updated cart info
            cart_serializer = CartSerializer(cart, context={'request': request})
            
            logger.info(f"Updated cart item quantity for user {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Cart item updated successfully',
                'cart': cart_serializer.data
            })
        
        return Response({
            'success': False,
            'message': 'Invalid data provided',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except CartItem.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Item not found in cart'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to update cart item',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout_cart(request):
    """
    Checkout cart and create order
    POST /cart/checkout/
    """
    serializer = CheckoutSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                cart = get_or_create_cart(request.user)
                
                # Check if cart is empty
                if cart.is_empty:
                    return Response({
                        'success': False,
                        'message': 'Cart is empty'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check stock availability for all items
                unavailable_items = []
                for cart_item in cart.cart_items.all():
                    if not cart_item.is_available:
                        unavailable_items.append(cart_item.item.name)
                
                if unavailable_items:
                    return Response({
                        'success': False,
                        'message': 'Some items are no longer available',
                        'unavailable_items': unavailable_items
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Create order
                order = Order.objects.create(
                    customer=request.user,
                    shipping_address=serializer.validated_data['shipping_address'],
                    phone_number=serializer.validated_data['phone_number'],
                    delivery_instructions=serializer.validated_data.get('delivery_instructions', ''),
                    status='pending'
                )
                
                # Create order items and update stock
                for cart_item in cart.cart_items.all():
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        item=cart_item.item,
                        item_name=cart_item.item.name,
                        item_sku=cart_item.item.sku,
                        quantity=cart_item.quantity,
                        price=cart_item.item.price
                    )
                    
                    # Update stock
                    item = cart_item.item
                    item.quantity -= cart_item.quantity
                    item.save()
                    
                    # Log stock movement
                    StockMovement.objects.create(
                        item=item,
                        quantity_change=-cart_item.quantity,
                        reason="sale"
                    )
                
                # Calculate order totals
                order.calculate_totals()
                
                # Clear cart
                cart.clear()
                
                # Return order details
                order_serializer = OrderDetailSerializer(order)
                
                logger.info(f"Order created: {order.order_id} for user {request.user.username}")
                
                return Response({
                    'success': True,
                    'message': 'Order placed successfully',
                    'order': order_serializer.data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}")
            return Response({
                'success': False,
                'message': 'Checkout failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    """
    Clear all items from cart
    DELETE /cart/clear/
    """
    try:
        cart = get_or_create_cart(request.user)
        items_count = cart.total_items
        cart.clear()
        
        logger.info(f"Cart cleared for user {request.user.username} - {items_count} items removed")
        
        return Response({
            'success': True,
            'message': f'Cart cleared successfully - {items_count} items removed'
        })
    
    except Exception as e:
        logger.error(f"Error clearing cart: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to clear cart',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Additional helper views

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_count(request):
    """
    Get cart item count (for navbar/header display)
    GET /cart/count/
    """
    try:
        cart = get_or_create_cart(request.user)
        
        return Response({
            'success': True,
            'count': cart.total_items,
            'total_price': float(cart.total_price)
        })
    
    except Exception as e:
        logger.error(f"Error getting cart count: {str(e)}")
        return Response({
            'success': False,
            'message': 'Failed to get cart count',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



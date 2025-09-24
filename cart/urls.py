from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('info/', views.cart_info, name='cart_info'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout_cart, name='checkout'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('count/', views.cart_count, name='cart_count')
]
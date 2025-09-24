from django.urls import path
from . import views

urlpatterns = [
    # Main shop endpoints
    path('list/', views.shop_item_list, name='shop_item_list'),
    path('item/<int:item_id>/', views.shop_item_detail, name='shop_item_detail'),
    # Category and navigation
    path('categories/', views.shop_categories, name='shop_categories'),
    # Search and filtering helpers
    path('search-suggestions/', views.shop_search_suggestions, name='shop_search_suggestions'),
    path('price-range/', views.shop_price_range, name='shop_price_range'),
]
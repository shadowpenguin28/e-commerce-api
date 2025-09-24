# inventory/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Item management
    path('list/', views.list_items, name='list_items'),
    path('new/', views.create_item, name='create_item'),
    path('update/<int:item_id>/', views.update_item, name='update_item'),
    path('restock/<int:item_id>/', views.restock_item, name='restock_item'),
    
    # Order and revenue management
    path('orders/', views.view_orders, name='view_orders'),
    path('revenue/', views.revenue_report, name='revenue_report'),
    
    # Helper endpoints
    path('categories/', views.list_categories, name='list_categories'),
    path('stock-movements/<int:item_id>/', views.stock_movements, name='stock_movements'),
]
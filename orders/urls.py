from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('past/', views.past_orders, name='past_orders'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('new/', views.create_order, name='create_order'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('status/<int:order_id>/', views.order_status, name='order_status'),
    path('summary/', views.order_summary, name='order_summary')
]
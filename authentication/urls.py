from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # User authentication
    path('user/signup/', views.user_signup, name='user_signup'),
    path('user/login/', views.user_login, name='user_login'),
    
    # Shopkeeper authentication  
    path('admin/login/', views.shopkeeper_login, name='shopkeeper_login'),
    
    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile and logout
    path('profile/', views.user_profile, name='user_profile'),
    path('logout/', views.logout, name='logout'),
]
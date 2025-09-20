from rest_framework import permissions

class IsShopkeeper(permissions.BasePermission):
    """
    Custom permission to only allow shopkeepers to access certain views.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and is a shopkeeper
        return (
            request.user.is_authenticated and 
            request.user.role == 'shopkeeper'
        )


class IsUser(permissions.BasePermission):
    """
    Custom permission to only allow regular users to access certain views.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated and is a regular user
        return (
            request.user.is_authenticated and 
            request.user.role == 'user'
        )


class IsOwnerOrShopkeeper(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or shopkeepers to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is the owner or a shopkeeper
        if request.user.role == 'shopkeeper':
            return True
        
        # Check if object has a user/customer field and user owns it
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'customer'):
            return obj.customer == request.user
        
        return False


# Convenience functions for use in function-based views
def is_shopkeeper(user):
    """Check if user is a shopkeeper"""
    return user.is_authenticated and user.role == 'shopkeeper'


def is_user(user):
    """Check if user is a regular user"""
    return user.is_authenticated and user.role == 'user'
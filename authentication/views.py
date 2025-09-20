from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
import logging

from .serializers import (
    UserSignupSerializer, 
    UserLoginSerializer, 
    ShopkeeperLoginSerializer,
    UserProfileSerializer
)
from .models import CustomUser

# Set up logging
logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    """
    Generate JWT tokens for a user
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def user_signup(request):
    """
    User registration endpoint
    POST /auth/user/signup
    """
    serializer = UserSignupSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            # Create the user
            user = serializer.save()
            
            # Generate tokens
            tokens = get_tokens_for_user(user)
            
            # Get user profile data
            profile_data = UserProfileSerializer(user).data
            
            logger.info(f"New user registered: {user.username}")
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'user': profile_data,
                'tokens': tokens
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error during user signup: {str(e)}")
            return Response({
                'success': False,
                'message': 'Registration failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    """
    User login endpoint
    POST /auth/user/login
    """
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        # Get user profile data
        profile_data = UserProfileSerializer(user).data
        
        # Update last login
        login(request, user)
        
        logger.info(f"User logged in: {user.username}")
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': profile_data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'message': 'Invalid credentials',
        'errors': serializer.errors
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def shopkeeper_login(request):
    """
    Shopkeeper/Admin login endpoint
    POST /auth/admin/login
    """
    serializer = ShopkeeperLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        # Get user profile data
        profile_data = UserProfileSerializer(user).data
        
        # Update last login
        login(request, user)
        
        logger.info(f"Shopkeeper logged in: {user.username}")
        
        return Response({
            'success': True,
            'message': 'Shopkeeper login successful',
            'user': profile_data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'message': 'Access denied',
        'errors': serializer.errors
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
def user_profile(request):
    """
    Get current user profile (requires authentication)
    GET /auth/profile
    """
    if request.user.is_authenticated:
        profile_data = UserProfileSerializer(request.user).data
        return Response({
            'success': True,
            'user': profile_data
        })
    
    return Response({
        'success': False,
        'message': 'Authentication required'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout(request):
    """
    Logout user by blacklisting refresh token
    POST /auth/logout
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the refresh token
            
            logger.info(f"User logged out: {request.user.username}")
            
            return Response({
                'success': True,
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Refresh token required'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Logout failed',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
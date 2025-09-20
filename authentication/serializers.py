from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class UserSignupSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        help_text="Password must meet Django's validation requirements"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirm password"
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'address', 'password', 'password_confirm']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        """
        Validate that passwords match
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_email(self, value):
        """
        Check that email is unique
        """
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def create(self, validated_data):
        """
        Create user with hashed password
        """
        # Remove password_confirm from validated_data
        validated_data.pop('password_confirm')
        
        # Create user with role 'user' (default)
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            address=validated_data.get('address', ''),
            role='user'  # Force role to be 'user'
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Authenticate user
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid username or password')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            # Check if user has 'user' role
            if user.role != 'user':
                raise serializers.ValidationError('Invalid credentials for user login')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class ShopkeeperLoginSerializer(serializers.Serializer):
    """
    Serializer for shopkeeper/admin login
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Authenticate user
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid username or password')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            # Check if user has 'shopkeeper' role
            if user.role != 'shopkeeper':
                raise serializers.ValidationError('Access denied. Shopkeeper credentials required.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data (for responses)
    """
    full_name = serializers.ReadOnlyField()
    is_shopkeeper = serializers.ReadOnlyField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'full_name', 'phone_number', 'address', 'role', 
                 'is_shopkeeper', 'date_joined']
        read_only_fields = ['id', 'username', 'role', 'date_joined']
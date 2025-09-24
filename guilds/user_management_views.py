from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User


# User Management API endpoints
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def user_list(request):
    """Get list of all users (staff only)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        users = User.objects.all().order_by('-date_joined')
        user_data = []
        
        for user in users:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        return Response({
            'success': True,
            'users': user_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_user(request):
    """Create a new user (staff only)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        is_staff = request.data.get('is_staff', False)
        is_active = request.data.get('is_active', True)
        
        # Validate required fields
        if not username:
            return Response({
                'success': False,
                'error': 'Username is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not password:
            return Response({
                'success': False,
                'error': 'Password is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response({
                'success': False,
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if email already exists (if provided)
        if email and User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_active=is_active
        )
        
        return Response({
            'success': True,
            'message': f'User {username} created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat()
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """Update user information (staff only)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update fields if provided
        if 'username' in request.data:
            # Check if new username already exists
            new_username = request.data['username']
            if new_username != user.username and User.objects.filter(username=new_username).exists():
                return Response({
                    'success': False,
                    'error': 'Username already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.username = new_username
        
        if 'email' in request.data:
            # Check if new email already exists
            new_email = request.data['email']
            if new_email != user.email and new_email and User.objects.filter(email=new_email).exists():
                return Response({
                    'success': False,
                    'error': 'Email already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.email = new_email
        
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        
        if 'is_staff' in request.data:
            user.is_staff = request.data['is_staff']
        
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
        
        user.save()
        
        return Response({
            'success': True,
            'message': f'User {user.username} updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    """Delete a user (staff only, cannot delete superuser)"""
    try:
        # Check if user is staff
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Permission denied. Staff access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Prevent deletion of superusers
        if user.is_superuser:
            return Response({
                'success': False,
                'error': 'Cannot delete superuser accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent self-deletion
        if user.id == request.user.id:
            return Response({
                'success': False,
                'error': 'Cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        username = user.username
        user.delete()
        
        return Response({
            'success': True,
            'message': f'User {username} deleted successfully'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

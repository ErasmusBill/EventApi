from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import UserSerializer
from rest_framework import status
import uuid
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.throttling import UserRateThrottle
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.contrib.auth import authenticate

class UserRegistration(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            verification_token = str(uuid.uuid4())
            user.verification_token = verification_token
            user.verification_token_expiry = timezone.now() + timezone.timedelta(hours=24)
            user.save()
            print(f"Verification Token: {verification_token}")
            return Response(
                {
                    "message": "You are registered successfully. Please verify your email",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@receiver(post_save, sender=User)
def send_verification_token(sender, instance, created, **kwargs):
    if created:
        verification_token = instance.verification_token
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        verification_url = f"{base_url}/api/users/verify-email/{verification_token}/"
        
        subject = "Verify your email address"
        html_message = f"""
        <p>Hi {instance.username},</p>
        <p>Please click the link below to verify your email address:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """
        plain_message = f"""
        Hi {instance.username},
        Please click the link below to verify your email address: {verification_url}
        If you didn't request this, you can safely ignore this email.
        """
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error
            print(f"Failed to send verification email: {e}")
            
class VerifyEmailView(APIView):
    def get(self, request, token):
        user = get_object_or_404(User, verification_token=token)   
        
        if user.verification_token_expiry and user.verification_token_expiry > timezone.now():
            user.is_verified = True
            user.verification_token = None
            user.verification_token_expiry = None
            user.save()
            return Response({"message":"Email verified successfully"}, status=status.HTTP_200_OK)     
        else:
            return Response({"error":"Invalid or expired verification token"}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    throttle_classes = [UserRateThrottle] 
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_verified:
            return Response({'error': 'Email not verified'}, status=status.HTTP_403_FORBIDDEN)
        
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'message': 'Login successful',
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh)
            },
            status=status.HTTP_200_OK
        )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated] 
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_400_BAD_REQUEST)

class UpdateProfile(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
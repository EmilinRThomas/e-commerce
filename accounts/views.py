# accounts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import (
    SignupSerializer, VerifyOTPSerializer, ResendOTPSerializer,
    LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    ChangePasswordSerializer,
)
from .models import User, OTP
from .utils import create_and_send_otp

class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp = create_and_send_otp(user, purpose='signup')
            return Response({
                "detail": "User created. OTP sent.", 
                "otp_debug": otp.otp
            }, status=status.HTTP_201_CREATED)
        else:
            # Return detailed validation errors
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            now = timezone.now()
            otp_qs = OTP.objects.filter(user=user, otp=otp_code, is_used=False, expires_at__gte=now)
            if not otp_qs.exists():
                return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
            
            otp = otp_qs.latest('created_at')
            otp.is_used = True
            otp.save()
            user.is_active = True
            user.is_verified = True
            user.save()
            
            # Generate JWT tokens after successful verification
            refresh = RefreshToken.for_user(user)
            return Response({
                "detail": "Email verified successfully.",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                }
            })
        else:
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            otp = create_and_send_otp(user, purpose='signup')
            return Response({
                "detail": "OTP resent.", 
                "otp_debug": otp.otp
            })
        else:
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(request, username=username, password=password)
            
            if not user:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            if not user.is_verified:
                return Response({"detail": "Email not verified"}, status=status.HTTP_403_FORBIDDEN)
            
            refresh = RefreshToken.for_user(user)
            return Response({
                "detail": "Login successful",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                },
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            })
        else:
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            otp = create_and_send_otp(user, purpose='forgot')
            return Response({
                "detail": "OTP sent for password reset.", 
                "otp_debug": otp.otp
            })
        else:
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            now = timezone.now()
            otp_qs = OTP.objects.filter(user=user, otp=otp_code, purpose='forgot', is_used=False, expires_at__gte=now)
            if not otp_qs.exists():
                return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
            
            otp = otp_qs.latest('created_at')
            otp.is_used = True
            otp.save()
            user.set_password(new_password)
            user.save()
            
            return Response({"detail": "Password reset successful."})
        else:
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            old = serializer.validated_data['old_password']
            new = serializer.validated_data['new_password']
            user = request.user
            
            if not user.check_password(old):
                return Response({"detail": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(new)
            user.save()
            return Response({"detail": "Password changed successfully."})
        else:
            return Response({
                "detail": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
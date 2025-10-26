# orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, CreateRazorpayOrderView, VerifyRazorpayPaymentView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
    # Legacy endpoints (keep for compatibility)
    path('create-order/', CreateRazorpayOrderView.as_view(), name='create-order'),
    path('verify-payment/', VerifyRazorpayPaymentView.as_view(), name='verify-payment'),
]
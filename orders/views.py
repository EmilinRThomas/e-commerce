from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
import razorpay
from decimal import Decimal
import random
import string

from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer
from products.models import CartItem

# Initialize Razorpay client
try:
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
except:
    client = None

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')

    @action(detail=False, methods=['post'])
    def place_order(self, request):
        """Create order from cart items"""
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            return Response({
                'order_id': order.id,
                'razorpay_order_id': order.razorpay_order_id,
                'amount': float(order.total_amount),
                'currency': 'INR'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """Verify payment and clear cart"""
        data = request.data
        order_id = data.get('order_id')
        
        if not order_id:
            return Response({'detail': 'Order ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id, user=request.user)
            
            # For testing, simulate successful payment
            order.status = 'placed'
            order.save()
            
            # Clear user's cart
            CartItem.objects.filter(user=request.user).delete()
            
            return Response({
                'detail': 'Payment verified and order placed successfully.',
                'order_id': order.id,
                'status': order.status
            })
            
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        """Get user's order history"""
        orders = self.get_queryset().order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get specific order details"""
        try:
            order = self.get_queryset().get(pk=pk)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

# Legacy views for simple Razorpay integration
class CreateRazorpayOrderView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        if not amount:
            return Response({"detail": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount_paisa = int(Decimal(str(amount)) * 100)
            data = {
                'amount': amount_paisa,
                'currency': 'INR',
                'payment_capture': 1
            }
            if client:
                order = client.order.create(data=data)
            else:
                # Fallback for testing
                order = {
                    "id": "order_test_" + ''.join(random.choices(string.ascii_letters + string.digits, k=10)),
                    "amount": amount_paisa,
                    "currency": "INR"
                }
            return Response(order)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class VerifyRazorpayPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        payload = {
            'razorpay_payment_id': request.data.get('razorpay_payment_id'),
            'razorpay_order_id': request.data.get('razorpay_order_id'),
            'razorpay_signature': request.data.get('razorpay_signature'),
        }
        try:
            if client:
                client.utility.verify_payment_signature(payload)
            return Response({"detail": "Payment verified successfully"})
        except Exception as e:
            return Response({"detail": "Invalid signature", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
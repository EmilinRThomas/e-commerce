from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer, ProductVariantSerializer
from products.models import Product, ProductVariant
from django.db import transaction
import random
import string

class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = serializers.SerializerMethodField()
    variant_detail = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'variant', 'quantity', 'unit_price', 'total_price', 'product_detail', 'variant_detail']

    def get_product_detail(self, obj):
        return ProductSerializer(obj.product).data

    def get_variant_detail(self, obj):
        if obj.variant:
            return ProductVariantSerializer(obj.variant).data
        return None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'total_amount', 'status', 'razorpay_order_id', 'razorpay_payment_id', 'created_at', 'items']
        read_only_fields = ['id', 'user', 'status', 'razorpay_order_id', 'razorpay_payment_id', 'created_at']

class OrderCreateSerializer(serializers.Serializer):
    """
    Creates an Order from user's cart
    Computes total, stores Order with status 'pending'
    Returns order info including razorpay_order_id
    """
    
    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        cart_items = user.cart_items.select_related('variant__product').all()
        
        if not cart_items:
            raise serializers.ValidationError("Cart is empty.")

        with transaction.atomic():
            # Calculate total from cart items
            total = sum([item.quantity * item.variant.price for item in cart_items])
            
            # Create order
            order = Order.objects.create(
                user=user, 
                total_amount=total, 
                status='pending'
            )

            # Create order items from cart
            for cart_item in cart_items:
                unit_price = cart_item.variant.price
                total_price = unit_price * cart_item.quantity
                
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.variant.product,
                    variant=cart_item.variant,
                    quantity=cart_item.quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
            
            # Generate razorpay order ID
            razorpay_order_id = "order_" + ''.join(random.choices(string.ascii_letters + string.digits, k=14))
            order.razorpay_order_id = razorpay_order_id
            order.save()
            
        return order
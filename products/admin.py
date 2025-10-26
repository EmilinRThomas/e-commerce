# products/admin.py
from django.contrib import admin
from .models import Category, Product, ProductVariant, CartItem, WishlistItem

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(CartItem)
admin.site.register(WishlistItem)

# products/urls.py
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, ProductVariantViewSet,
    CartViewSet, WishlistViewSet
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')  # Added basename
router.register('products', ProductViewSet, basename='product')     # Added basename
router.register('variants', ProductVariantViewSet, basename='variant')  # Added basename
router.register('cart', CartViewSet, basename='cart')
router.register('wishlist', WishlistViewSet, basename='wishlist')

urlpatterns = router.urls
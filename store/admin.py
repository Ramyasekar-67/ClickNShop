from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import Product, CartItem, Order, OrderItem, Wishlist, Review


# =========================================================
# PRODUCT ADMIN
# =========================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'original_price',
        'discount',
        'stock',
        'rating',
        'featured',
        'created_at',
    )

    list_filter = (
        'category',
        'featured',
        'stock',
        'created_at',
    )

    search_fields = (
        'name',
        'description',
        'category',
    )

    list_editable = (
        'price',
        'stock',
        'featured',
    )

    ordering = ('-created_at',)

    date_hierarchy = 'created_at'


# =========================================================
# CART ITEM ADMIN
# =========================================================

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'product',
        'quantity',
        'created_at',
    )

    list_filter = (
        'created_at',
    )

    search_fields = (
        'user__username',
        'product__name',
    )

    ordering = ('-created_at',)

    date_hierarchy = 'created_at'


# =========================================================
# ORDER ADMIN
# =========================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'full_name',
        'total_amount',
        'payment_method',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'payment_method',
        'created_at',
    )

    search_fields = (
        'user__username',
        'full_name',
        'phone',
        'pincode',
        'city',
        'state',
    )

    ordering = ('-created_at',)

    date_hierarchy = 'created_at'

    actions = [
        'mark_processing',
        'mark_shipped',
        'mark_delivered',
        'mark_cancelled',
    ]

    @admin.action(description='Mark selected orders as Processing')
    def mark_processing(self, request, queryset):
        queryset.update(status='Processing')

    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        queryset.update(status='Shipped')

    @admin.action(description='Mark selected orders as Delivered')
    def mark_delivered(self, request, queryset):
        queryset.update(status='Delivered')

    @admin.action(description='Mark selected orders as Cancelled')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='Cancelled')


# =========================================================
# ORDER ITEM ADMIN
# =========================================================

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'product',
        'quantity',
        'price',
    )

    search_fields = (
        'order__id',
        'product__name',
    )

    ordering = ('-order__created_at',)


# =========================================================
# WISHLIST ADMIN
# =========================================================

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'product',
        'created_at',
    )

    search_fields = (
        'user__username',
        'product__name',
    )

    list_filter = (
        'created_at',
    )

    ordering = ('-created_at',)

    date_hierarchy = 'created_at'


# =========================================================
# REVIEW ADMIN
# =========================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'user',
        'rating',
        'created_at',
    )

    list_filter = (
        'rating',
        'created_at',
    )

    search_fields = (
        'product__name',
        'user__username',
        'comment',
    )

    ordering = ('-created_at',)

    date_hierarchy = 'created_at'


# =========================================================
# USER ADMIN
# =========================================================

# Remove Django's default User admin
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'date_joined',
    )

    list_filter = (
        'is_staff',
        'is_active',
        'is_superuser',
        'date_joined',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    ordering = ('-date_joined',)

    date_hierarchy = 'date_joined'
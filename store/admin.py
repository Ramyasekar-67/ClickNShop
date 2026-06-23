from django.contrib import admin
from .models import Product, Cart, Coupon


admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Coupon)
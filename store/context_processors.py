from django.contrib.auth.models import User
from .models import Product, Order


def clicknshop_admin_summary(request):
    if not request.path.startswith('/admin/'):
        return {}
    products = Product.objects.all()
    return {
        'clicknshop_total_products': products.count(),
        'clicknshop_total_stock': sum(products.values_list('stock', flat=True)) or 0,
        'clicknshop_total_orders': Order.objects.count(),
        'clicknshop_total_customers': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'clicknshop_low_stock': products.filter(stock__gt=0, stock__lte=5).count(),
        'clicknshop_out_stock': products.filter(stock=0).count(),
    }

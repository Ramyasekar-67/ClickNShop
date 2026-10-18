import csv
from decimal import Decimal, ROUND_HALF_UP

import razorpay
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils.http import url_has_allowed_host_and_scheme
from functools import wraps

from .models import Product, CartItem, Order, OrderItem, Wishlist, Review
from .forms import RegisterForm, CheckoutForm

LOW_STOCK_LIMIT = 5
TWO_PLACES = Decimal('0.01')


def money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def safe_next(request, default):
    """Return the ?next= / posted next URL only if it is a safe local URL."""
    target = request.POST.get('next') or request.GET.get('next') or ''
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return default


def admin_required(view):
    """Server-side guard: only active staff users may open admin pages."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path(), login_url='/my-admin-login/')
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def reduce_stock(product, quantity):
    product.stock = max(0, product.stock - quantity)
    product.save(update_fields=['stock'])


@login_required
def home(request):
    products = Product.objects.all().order_by('-created_at')

    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', '')

    if search:
        products = products.filter(
            name__icontains=search
        )

    if category:
        products = products.filter(
            category=category
        )

    if sort == 'price_low':
        products = products.order_by('price')

    elif sort == 'price_high':
        products = products.order_by('-price')

    elif sort == 'newest':
        products = products.order_by('-created_at')

    elif sort == 'name':
        products = products.order_by('name')

    # Pagination
    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    categories = Product.CATEGORY_CHOICES

    # Wishlist products for logged-in user
    wishlist_product_ids = []

    if request.user.is_authenticated:
        wishlist_product_ids = list(
            Wishlist.objects.filter(
                user=request.user
            ).values_list(
                'product_id',
                flat=True
            )
        )

    return render(request, 'store/home.html', {
        'products': products,
        'categories': categories,
        'search': search,
        'selected_category': category,
        'selected_sort': sort,
        'wishlist_product_ids': wishlist_product_ids,
    })


@login_required
def category_products(request, category):
    products = Product.objects.filter(
        category=category
    ).order_by('-created_at')

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    wishlist_product_ids = []

    if request.user.is_authenticated:
        wishlist_product_ids = list(
            Wishlist.objects.filter(
                user=request.user
            ).values_list(
                'product_id',
                flat=True
            )
        )

    return render(request, 'store/category_products.html', {
        'products': products,
        'category': category,
        'wishlist_product_ids': wishlist_product_ids,
    })    


@login_required
def product_detail(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id
    )

    related_products = Product.objects.filter(
        category=product.category
    ).exclude(
        id=product.id
    )[:4]

    wishlist_item = None

    if request.user.is_authenticated:
        wishlist_item = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).first()

    # Product reviews
    reviews = Review.objects.filter(
        product=product
    ).select_related(
        'user'
    ).order_by(
        '-created_at'
    )

    # Average rating
    review_count = reviews.count()

    if review_count > 0:
        average_rating = sum(
            review.rating for review in reviews
        ) / review_count
    else:
        average_rating = 0

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'wishlist_item': wishlist_item,
        'reviews': reviews,
        'review_count': review_count,
        'average_rating': average_rating,
    })


@login_required
def add_review(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id
    )

    if request.method == 'POST':

        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not comment:
            messages.error(
                request,
                'Please provide a rating and review.'
            )

            return redirect(
                'product_detail',
                product_id=product.id
            )

        try:
            rating = int(rating)
        except ValueError:
            messages.error(
                request,
                'Invalid rating.'
            )

            return redirect(
                'product_detail',
                product_id=product.id
            )

        if rating < 1 or rating > 5:
            messages.error(
                request,
                'Rating must be between 1 and 5 stars.'
            )

            return redirect(
                'product_detail',
                product_id=product.id
            )

        # Check if user already reviewed this product
        existing_review = Review.objects.filter(
            product=product,
            user=request.user
        ).first()

        if existing_review:
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.save()

            messages.success(
                request,
                'Your review has been updated.'
            )

        else:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment
            )

            messages.success(
                request,
                'Your review has been added successfully.'
            )

        return redirect(
            'product_detail',
            product_id=product.id
        )

    return redirect(
        'product_detail',
        product_id=product.id
    )


def register(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            # Public registration must only create ordinary customer accounts.
            user.is_staff = False
            user.is_superuser = False
            user.set_password(form.cleaned_data['password'])
            user.save()

            messages.success(
                request,
                'Account created successfully. Please login.'
            )

            return redirect('login')

    else:
        form = RegisterForm()

    return render(request, 'store/register.html', {
        'form': form
    })


def user_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_active and not user.is_staff:
            login(request, user)
            target = safe_next(request, '')
            # Customers may never be sent into admin pages.
            if target.startswith(('/admin/', '/my-admin')):
                target = ''
            return redirect(target or 'home')
        elif user is not None and user.is_staff:
            messages.error(request, 'This is a staff account. Please use the Admin Login.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'store/login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def cart(request):
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product')

    total = sum(
        item.subtotal()
        for item in cart_items
    )

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id
    )

    if product.stock <= 0:
        messages.error(
            request,
            'This product is out of stock.'
        )

        return redirect(
            'product_detail',
            product_id=product.id
        )

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:

        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()

        else:
            messages.warning(
                request,
                'You have reached the available stock.'
            )

            return redirect('cart')

    messages.success(
        request,
        f'{product.name} added to your cart.'
    )

    return redirect('cart')


@login_required
def increase_quantity(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    if cart_item.quantity < cart_item.product.stock:
        cart_item.quantity += 1
        cart_item.save()

    else:
        messages.warning(
            request,
            'Maximum available stock reached.'
        )

    return redirect('cart')


@login_required
def decrease_quantity(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    else:
        cart_item.delete()

    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    cart_item.delete()

    messages.success(
        request,
        'Product removed from your cart.'
    )

    return redirect('cart')


@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product')

    if not cart_items.exists():
        messages.warning(
            request,
            'Your cart is empty.'
        )
        return redirect('cart')

    total = sum(
        item.subtotal()
        for item in cart_items
    )

    if request.method == 'POST':

        form = CheckoutForm(request.POST)

        if form.is_valid():

            for item in cart_items:
                if item.quantity > item.product.stock:
                    messages.error(
                        request,
                        f'Not enough stock for {item.product.name}.'
                    )
                    return redirect('cart')

            payment_method = form.cleaned_data['payment_method']

            # COD
            if payment_method == 'COD':

                order = Order.objects.create(
                    user=request.user,
                    full_name=form.cleaned_data['full_name'],
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    state=form.cleaned_data['state'],
                    pincode=form.cleaned_data['pincode'],
                    payment_method=payment_method,
                    payment_status='COD',
                    total_amount=total,
                )

                for item in cart_items:

                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price_with_gst,
                        gst_rate=item.product.gst_rate,
                    )

                    reduce_stock(item.product, item.quantity)

                cart_items.delete()

                messages.success(
                    request,
                    'Your order has been placed successfully!'
                )

                return render(request, 'store/order_success.html', {
                    'order': order,
                })

            # Razorpay
            client = razorpay.Client(
                auth=(
                    settings.RAZORPAY_KEY_ID,
                    settings.RAZORPAY_KEY_SECRET
                )
            )

            razorpay_order = client.order.create({
                'amount': int(money(total) * 100),
                'currency': 'INR',
                'receipt': f'clicknshop_{request.user.id}_{int(money(total) * 100)}',
            })

            order = Order.objects.create(
                user=request.user,
                full_name=form.cleaned_data['full_name'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state'],
                pincode=form.cleaned_data['pincode'],
                payment_method=payment_method,
                payment_status='Pending',
                razorpay_order_id=razorpay_order['id'],
                total_amount=total,
            )

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price_with_gst,
                    gst_rate=item.product.gst_rate,
                )

            return render(request, 'store/checkout.html', {
                'form': form,
                'cart_items': cart_items,
                'total': total,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'order_id': order.id,
            })

    else:
        form = CheckoutForm()

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total,
    })


# =========================
# MY ORDERS
# =========================

@login_required
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related(
        'items__product'
    ).order_by(
        '-created_at'
    )

    return render(request, 'store/my_orders.html', {
        'orders': orders
    })


# =========================
# ORDER DETAIL
# =========================

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__product'
        ),
        id=order_id,
        user=request.user
    )

    return render(request, 'store/order_detail.html', {
        'order': order
    })


# =========================
# WISHLIST
# =========================

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id
    )

    wishlist_item = Wishlist.objects.filter(
        user=request.user,
        product=product
    ).first()

    if wishlist_item:
        wishlist_item.delete()

        messages.success(
            request,
            f'{product.name} removed from your wishlist.'
        )

    else:
        Wishlist.objects.create(
            user=request.user,
            product=product
        )

        messages.success(
            request,
            f'{product.name} added to your wishlist.'
        )

    return redirect(
        request.META.get(
            'HTTP_REFERER',
            'home'
        )
    )


@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related(
        'product'
    ).order_by(
        '-created_at'
    )

    return render(request, 'store/wishlist.html', {
        'wishlist_items': wishlist_items
    })


# =========================
# VERIFY RAZORPAY PAYMENT
# =========================

@login_required
def verify_payment(request):
    if request.method == 'POST':

        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        try:
            client = razorpay.Client(
                auth=(
                    settings.RAZORPAY_KEY_ID,
                    settings.RAZORPAY_KEY_SECRET
                )
            )

            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            order = Order.objects.get(
                razorpay_order_id=razorpay_order_id,
                user=request.user
            )

            if order.payment_status != 'Paid':
                order.razorpay_payment_id = razorpay_payment_id
                order.payment_status = 'Paid'
                order.status = 'Processing'
                order.save()

                for item in order.items.all():
                    if item.product:
                        reduce_stock(item.product, item.quantity)

            CartItem.objects.filter(
                user=request.user
            ).delete()

            messages.success(
                request,
                'Payment successful! Your order has been placed.'
            )

            return render(
                request,
                'store/order_success.html',
                {
                    'order': order
                }
            )

        except Exception:
            messages.error(
                request,
                'Payment verification failed.'
            )

            return redirect('checkout')

    return redirect('checkout')



# =========================================================
# ADMIN AREA (staff only)
# =========================================================

def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff and request.user.is_active:
        return redirect(safe_next(request, '') or 'admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active and user.is_staff:
            login(request, user)
            return redirect(safe_next(request, '') or 'admin_dashboard')

        messages.error(request, 'Invalid credentials or admin access denied.')

    return render(request, 'store/admin_login.html', {
        'next': request.GET.get('next', ''),
    })


def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


def _counted_orders():
    """Orders that count as real sales: not cancelled and not awaiting payment."""
    return Order.objects.exclude(status='Cancelled').exclude(payment_status='Pending')


@admin_required
def admin_dashboard(request):
    products = Product.objects.all()
    low_stock_products = products.filter(
        stock__gt=0, stock__lte=LOW_STOCK_LIMIT
    ).order_by('stock', 'name')
    out_of_stock_products = products.filter(stock=0).order_by('name')
    total_sales = _counted_orders().aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    return render(request, 'store/admin_dashboard.html', {
        'total_products': products.count(),
        'total_orders': Order.objects.count(),
        'total_customers': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'total_stock_units': products.aggregate(t=Sum('stock'))['t'] or 0,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_products': out_of_stock_products,
        'out_of_stock_count': out_of_stock_products.count(),
        'total_sales': total_sales,
        'recent_orders': Order.objects.order_by('-created_at')[:8],
        'active': 'dashboard',
    })


def _parse_non_negative_int(raw):
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


@admin_required
def admin_inventory(request):
    """Stock management: view availability and update stock quantities."""
    if request.method == 'POST':
        updated, errors = 0, []
        for product in Product.objects.all():
            raw = request.POST.get(f'stock_{product.id}')
            if raw is None:
                continue
            value = _parse_non_negative_int(raw)
            if value is None:
                errors.append(f'{product.name}: stock must be a whole number, 0 or more.')
                continue
            if value != product.stock:
                product.stock = value
                product.save(update_fields=['stock'])
                updated += 1
        for error in errors:
            messages.error(request, error)
        if updated:
            messages.success(request, f'Stock updated for {updated} product(s).')
        elif not errors:
            messages.info(request, 'No stock changes were made.')
        return redirect('admin_inventory')

    flt = request.GET.get('filter', '')
    products = Product.objects.all().order_by('category', 'name')
    if flt == 'low':
        products = products.filter(stock__gt=0, stock__lte=LOW_STOCK_LIMIT)
    elif flt == 'out':
        products = products.filter(stock=0)

    return render(request, 'store/admin_inventory.html', {
        'products': products,
        'filter': flt,
        'low_limit': LOW_STOCK_LIMIT,
        'active': 'inventory',
    })


@admin_required
def admin_gst(request):
    """GST management: set the GST rate per product or for a whole category."""
    if request.method == 'POST':
        mode = request.POST.get('mode')

        def valid_rate(raw):
            try:
                rate = Decimal(str(raw).strip())
            except Exception:
                return None
            return rate.quantize(TWO_PLACES) if Decimal('0') <= rate <= Decimal('100') else None

        if mode == 'category':
            rate = valid_rate(request.POST.get('rate'))
            category = request.POST.get('category')
            valid_categories = [c for c, _ in Product.CATEGORY_CHOICES]
            if rate is None or category not in valid_categories:
                messages.error(request, 'Choose a category and a GST rate between 0 and 100.')
            else:
                count = Product.objects.filter(category=category).update(gst_rate=rate)
                messages.success(request, f'GST set to {rate}% for {count} product(s) in {category}.')
        else:
            updated, errors = 0, []
            for product in Product.objects.all():
                raw = request.POST.get(f'gst_{product.id}')
                if raw is None:
                    continue
                rate = valid_rate(raw)
                if rate is None:
                    errors.append(f'{product.name}: GST must be between 0 and 100.')
                    continue
                if rate != product.gst_rate:
                    product.gst_rate = rate
                    product.save(update_fields=['gst_rate'])
                    updated += 1
            for error in errors:
                messages.error(request, error)
            if updated:
                messages.success(request, f'GST updated for {updated} product(s). Past orders keep the rate they were bought at.')
            elif not errors:
                messages.info(request, 'No GST changes were made.')
        return redirect('admin_gst')

    return render(request, 'store/admin_gst.html', {
        'products': Product.objects.all().order_by('category', 'name'),
        'categories': Product.CATEGORY_CHOICES,
        'active': 'gst',
    })


@admin_required
def admin_orders(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    status = request.GET.get('status', '')
    if status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)
    return render(request, 'store/admin_orders.html', {
        'orders': orders,
        'status': status,
        'statuses': Order.STATUS_CHOICES,
        'active': 'orders',
    })


@admin_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product'),
        id=order_id,
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f'Order #{order.id} marked as {new_status}.')
        else:
            messages.error(request, 'Invalid order status.')
        return redirect('admin_order_detail', order_id=order.id)

    return render(request, 'store/admin_order_detail.html', {
        'order': order,
        'statuses': Order.STATUS_CHOICES,
        'active': 'orders',
    })


def _gst_split(line_total, rate):
    """Split a GST-inclusive amount into (taxable, gst). GST is counted once."""
    line_total = money(line_total)
    rate = Decimal(rate or 0)
    if not rate:
        return line_total, Decimal('0.00')
    taxable = money(line_total * 100 / (100 + rate))
    return taxable, line_total - taxable


@admin_required
def admin_reports(request):
    report_type = request.GET.get('type', 'inventory')
    if report_type not in ('inventory', 'sales', 'gst'):
        report_type = 'inventory'

    products = Product.objects.all().order_by('category', 'name')
    orders = Order.objects.order_by('-created_at')
    counted = _counted_orders()

    context = {'report_type': report_type, 'active': 'reports'}

    if report_type == 'sales':
        context.update({
            'orders': orders,
            'total_sales': counted.aggregate(t=Sum('total_amount'))['t'] or Decimal('0'),
            'counted_orders': counted.count(),
            'order_count': orders.count(),
        })

    elif report_type == 'gst':
        gst_rows = []
        totals = {'taxable': Decimal('0'), 'gst': Decimal('0'), 'total': Decimal('0')}
        legacy_rows = 0
        items = OrderItem.objects.filter(order__in=counted).select_related(
            'product', 'order'
        ).order_by('-order__created_at', 'id')
        for item in items:
            if item.gst_rate is not None:
                rate, estimated = item.gst_rate, False
            else:
                # Older order: rate was not saved then, use the product's current rate.
                rate = item.product.gst_rate if item.product else Decimal('0')
                estimated = True
                legacy_rows += 1
            line_total = money(item.price * item.quantity)
            taxable, gst_amount = _gst_split(line_total, rate)
            totals['taxable'] += taxable
            totals['gst'] += gst_amount
            totals['total'] += line_total
            gst_rows.append({
                'item': item, 'rate': rate, 'estimated': estimated,
                'taxable': taxable, 'gst_amount': gst_amount, 'line_total': line_total,
            })
        context.update({'gst_rows': gst_rows, 'totals': totals, 'legacy_rows': legacy_rows})

    else:
        context.update({
            'products': products,
            'total_stock_units': products.aggregate(t=Sum('stock'))['t'] or 0,
            'low_stock_count': products.filter(stock__gt=0, stock__lte=LOW_STOCK_LIMIT).count(),
            'out_of_stock_count': products.filter(stock=0).count(),
            'low_limit': LOW_STOCK_LIMIT,
        })

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="clicknshop_{report_type}_report.csv"'
        writer = csv.writer(response)
        if report_type == 'sales':
            writer.writerow(['Order ID', 'Date', 'Customer', 'Order Status', 'Payment Status', 'Total (INR)'])
            for order in orders:
                writer.writerow([order.id, order.created_at.strftime('%Y-%m-%d'), order.full_name,
                                 order.status, order.payment_status, order.total_amount])
        elif report_type == 'gst':
            writer.writerow(['Order ID', 'Date', 'Product', 'Quantity', 'GST Rate (%)',
                             'Taxable Amount (INR)', 'GST Amount (INR)', 'Total incl. GST (INR)', 'Rate Source'])
            for row in context['gst_rows']:
                item = row['item']
                writer.writerow([
                    item.order_id, item.order.created_at.strftime('%Y-%m-%d'),
                    item.product.name if item.product else 'Deleted product', item.quantity,
                    row['rate'], row['taxable'], row['gst_amount'], row['line_total'],
                    'Current product rate (older order)' if row['estimated'] else 'Saved at purchase',
                ])
        else:
            writer.writerow(['Product', 'Category', 'Price before GST (INR)', 'GST Rate (%)',
                             'Price incl. GST (INR)', 'Stock', 'Status'])
            for product in products:
                status = 'Out of stock' if product.stock == 0 else (
                    'Low stock' if product.stock <= LOW_STOCK_LIMIT else 'In stock')
                writer.writerow([product.name, product.category, product.price, product.gst_rate,
                                 product.price_with_gst, product.stock, status])
        return response

    return render(request, 'store/admin_reports.html', context)

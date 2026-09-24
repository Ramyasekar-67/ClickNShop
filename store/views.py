from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .models import Product, CartItem, Order, OrderItem, Wishlist, Review
from .forms import RegisterForm, CheckoutForm


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
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            user.set_password(
                form.cleaned_data['password']
            )

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
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            return redirect('home')

        messages.error(
            request,
            'Invalid username or password.'
        )

    return render(request, 'store/login.html')


def user_logout(request):
    logout(request)

    return redirect('home')


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

            order = Order.objects.create(
                user=request.user,
                full_name=form.cleaned_data['full_name'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state'],
                pincode=form.cleaned_data['pincode'],
                payment_method=form.cleaned_data['payment_method'],
                total_amount=total,
            )

            for item in cart_items:

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price,
                )

                item.product.stock -= item.quantity
                item.product.save()

            cart_items.delete()

            messages.success(
                request,
                'Your order has been placed successfully!'
            )

            return redirect('home')

    else:
        form = CheckoutForm()

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total,
    })


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
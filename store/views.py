from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, Coupon
from django.contrib.auth.forms import UserCreationForm
from .models import Order, OrderItem,Wishlist, Review
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.contrib.auth.models import User
from django.core.paginator import Paginator


def home(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    sort = request.GET.get('sort')

    products = Product.objects.all()

    # SEARCH
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )

    # CATEGORY
    if category:
        products = products.filter(category=category)

    # SORTING
    if sort == 'price_low':
        products = products.order_by('price')

    elif sort == 'price_high':
        products = products.order_by('-price')

    elif sort == 'name':
        products = products.order_by('name')

    # PAGINATION
    paginator = Paginator(products, 8)

    page_number = request.GET.get('page')

    products = paginator.get_page(page_number)

    # CART COUNT
    cart_count = 0

    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(
            user=request.user
        ).count()

    return render(request, 'home.html', {
        'products': products,
        'cart_count': cart_count,
        'query': query
    })

# ADD TO CART
def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return redirect('/login/')

    product = Product.objects.get(id=product_id)
    if product.stock <= 0:
        messages.error(
        request,
        'Product is out of stock!'
    )
        return redirect('/')
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(
        request,
        'Product added to cart successfully!'
    )

    return redirect('/')    



def cart_view(request):

    cart_items = Cart.objects.filter(user=request.user)

    total_price = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    discount = request.session.get('discount', 0)

    final_price = total_price - (
        total_price * discount / 100
    )

    return render(
        request,
        'cart.html',
        {
            'cart_items': cart_items,
            'total_price': total_price,
            'discount': discount,
            'final_price': final_price
        }
    )



# REMOVE ITEM
def remove_from_cart(request, cart_id):
    item = get_object_or_404(Cart, id=cart_id)
    item.delete()
    return redirect('cart')


# INCREASE QTY
def increase_qty(request, cart_id):
    item = get_object_or_404(Cart, id=cart_id)
    item.quantity += 1
    item.save()
    return redirect('cart')


# DECREASE QTY
def decrease_qty(request, cart_id):
    item = get_object_or_404(Cart, id=cart_id)

    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()

    return redirect('cart') 

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/login/')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})    



@login_required
def place_order(request):

    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        return redirect('cart')

    total = 0

    for item in cart_items:

        if item.quantity > item.product.stock:
            messages.error(
                request,
                f"Only {item.product.stock} items available for {item.product.name}."
            )
            return redirect('cart')

        total += item.product.price * item.quantity

    order = Order.objects.create(
        user=request.user,
        total_price=total
    )

    for item in cart_items:

        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

        # Reduce stock
        item.product.stock -= item.quantity
        item.product.save()

    cart_items.delete()

    return render(
        request,
        'success.html',
        {'order': order}
    ) 

def my_orders(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'orders.html', {
        'orders': orders
    })   


def product_detail(request, product_id):
    product = Product.objects.get(id=product_id)
    reviews = Review.objects.filter(product=product)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    related_products = Product.objects.exclude(id=product.id)[:4]
    return render(
        request,
        'product_detail.html',
        {
            'product': product,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'related_products': related_products
        }
    )



@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'orders.html', {
        'orders': orders
    })

@staff_member_required
def add_product(request):

    if request.method == "POST":

        Product.objects.create(
            name=request.POST['name'],
            description=request.POST['description'],
            price=request.POST['price'],
            category=request.POST['category'],
            image=request.FILES['image']
        )

        return redirect('/')

    return render(request, 'add_product.html')



@login_required
def add_to_wishlist(request, product_id):
    product = Product.objects.get(id=product_id)

    Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    return redirect('/')

@login_required
def add_review(request, product_id):

    if request.method == "POST":

        product = Product.objects.get(id=product_id)

        Review.objects.create(
            product=product,
            user=request.user,
            rating=request.POST['rating'],
            comment=request.POST['comment']
        )

    return redirect('product_detail', product_id=product_id)

def wishlist_view(request):

    wishlist_items = Wishlist.objects.filter(
        user=request.user
    )

    return render(
        request,
        'wishlist.html',
        {'wishlist_items': wishlist_items}
    )

@login_required
def profile_view(request):

    orders_count = Order.objects.filter(
        user=request.user
    ).count()

    wishlist_count = Wishlist.objects.filter(
        user=request.user
    ).count()

    context = {
        'orders_count': orders_count,
        'wishlist_count': wishlist_count
    }

    return render(
        request,
        'profile.html',
        context
    )

@staff_member_required
def seller_dashboard(request):

    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_revenue = 0
    products = Product.objects.all()
    recent_orders = Order.objects.order_by('-created_at')[:5]
    top_products = Product.objects.all()[:5]
    total_users = User.objects.count()

    for order in Order.objects.all():
        total_revenue += order.total_price

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'products': products,
        'recent_orders': recent_orders,
        ' top_products': top_products,
        'total_users': total_users
    }

    return render(
        request,
        'seller_dashboard.html',
        context
    )

def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        product.name = request.POST['name']
        product.price = request.POST['price']
        product.description = request.POST['description']
        product.save()
        return redirect('seller_dashboard')

    return render(request, 'edit_product.html', {
        'product': product
    })


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('seller_dashboard')


def checkout(request):
    cart_items = Cart.objects.filter(
        user=request.user
    )
    total_price = sum(
        item.product.price * item.quantity
        for item in cart_items
    )
    return render(
        request,
        'checkout.html',
        {
            'cart_items': cart_items,
            'total_price': total_price
        }
    )

def remove_from_wishlist(request, wishlist_id):
    item = Wishlist.objects.get(id=wishlist_id)
    item.delete()
    return redirect('wishlist')

def generate_invoice(request, order_id):
    order = Order.objects.get(id=order_id)
    response = HttpResponse(
        content_type='application/pdf'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="invoice_{order.id}.pdf"'
    )
    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(200, 800, "ClickNShop Invoice")
    p.setFont("Helvetica", 12)
    p.drawString(50, 750, f"Order ID: {order.id}")
    p.drawString(50, 730, f"Customer: {order.user.username}")
    p.drawString(50, 710, f"Total Amount: ₹{order.total_price}")
    p.drawString(50, 680, "Thank you for shopping with ClickNShop!")
    p.showPage()
    p.save()

    return response

def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code')
        try:
            coupon = Coupon.objects.get(
                code=code
            )
            request.session['discount'] = (
                coupon.discount
            )
            messages.success(
                request,
                f'Coupon {code} applied successfully!'
            )
        except Coupon.DoesNotExist:
            request.session['discount'] = 0
            messages.error(
                request,
                'Invalid coupon code!'
            )
    return redirect('cart')

def contact(request):
    return render(request, 'contact.html')
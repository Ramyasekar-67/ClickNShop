
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),

    path('remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('increase/<int:cart_id>/', views.increase_qty, name='increase_qty'),
    path('decrease/<int:cart_id>/', views.decrease_qty, name='decrease_qty'),
    path('register/', views.register, name='register'),
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    
    path('add-product/', views.add_product, name='add_product'),
    path('wishlist/add/<int:product_id>/',views.add_to_wishlist,name='add_to_wishlist'),
    path('review/<int:product_id>/',views.add_review,name='add_review'),
    path('wishlist/', views.wishlist_view,name='wishlist'),
    path('profile/',views.profile_view,name='profile'),
    path('seller-dashboard/',views.seller_dashboard,name='seller_dashboard'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    
    path('remove-wishlist/<int:wishlist_id>/',views.remove_from_wishlist,name='remove_from_wishlist'),
    path('invoice/<int:order_id>/',views.generate_invoice,name='invoice'),
    path('apply-coupon/',views.apply_coupon,name='apply_coupon'),
    path('contact/', views.contact, name='contact'),
]

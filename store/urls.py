from django.urls import path

from .views import (
    home,
    admin_dashboard,
    admin_reports,
    admin_inventory,
    admin_gst,
    admin_orders,
    admin_order_detail,
    admin_login_view,
    admin_logout_view,
    category_products,
    product_detail,
    register,
    user_login,
    user_logout,
    cart,
    add_to_cart,
    increase_quantity,
    decrease_quantity,
    remove_from_cart,
    checkout,
    verify_payment,
    my_orders,
    order_detail,
    add_to_wishlist,
    wishlist,
    add_review,
)


urlpatterns = [

    path(
        '',
        home,
        name='home'
    ),

    path(
        'my-admin-login/',
        admin_login_view,
        name='admin_login'
    ),

    path(
        'my-admin-logout/',
        admin_logout_view,
        name='admin_logout'
    ),

    path(
        'my-admin-dashboard/',
        admin_dashboard,
        name='admin_dashboard'
    ),

    path('my-admin-inventory/', admin_inventory, name='admin_inventory'),
    path('my-admin-gst/', admin_gst, name='admin_gst'),
    path('my-admin-orders/', admin_orders, name='admin_orders'),
    path('my-admin-orders/<int:order_id>/', admin_order_detail, name='admin_order_detail'),

    path(
        'my-admin-reports/',
        admin_reports,
        name='admin_reports'
    ),

    path(
       'category/<str:category>/',
        category_products,
        name='category_products'
    ),

    path(
        'product/<int:product_id>/',
        product_detail,
        name='product_detail'
    ),

    path(
        'register/',
        register,
        name='register'
    ),

    path(
        'login/',
        user_login,
        name='login'
    ),

    path(
        'logout/',
        user_logout,
        name='logout'
    ),

    path(
        'cart/',
        cart,
        name='cart'
    ),

    path(
        'cart/add/<int:product_id>/',
        add_to_cart,
        name='add_to_cart'
    ),

    path(
        'cart/increase/<int:item_id>/',
        increase_quantity,
        name='increase_quantity'
    ),

    path(
        'cart/decrease/<int:item_id>/',
        decrease_quantity,
        name='decrease_quantity'
    ),

    path(
        'cart/remove/<int:item_id>/',
        remove_from_cart,
        name='remove_from_cart'
    ),

    path(
        'checkout/',
        checkout,
        name='checkout'
    ),

    path(
        'verify-payment/',
        verify_payment,
        name='verify_payment'
    ),

    path(
        'my-orders/',
        my_orders,
        name='my_orders'
    ),

    path(
        'order/<int:order_id>/',
        order_detail,
        name='order_detail'
    ),

    # Wishlist
    path(
        'wishlist/add/<int:product_id>/',
        add_to_wishlist,
        name='add_to_wishlist'
    ),

    path(
        'wishlist/',
        wishlist,
        name='wishlist'
    ),

    path(
    'product/<int:product_id>/review/',
    add_review,
    name='add_review'
    ),

]
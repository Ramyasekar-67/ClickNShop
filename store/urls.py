from django.urls import path

from .views import (
    home,
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
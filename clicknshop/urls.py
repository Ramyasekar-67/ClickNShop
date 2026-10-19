"""
URL configuration for clicknshop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import path, include

def admin_login_redirect(request):
    # One staff login only: Django Admin's own login page sends staff to the ClickNShop admin login.
    target = '/my-admin-login/'
    nxt = request.GET.get('next')
    return redirect(f'{target}?{urlencode({"next": nxt})}' if nxt else target)


urlpatterns = [
    path('admin/login/', admin_login_redirect),
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
]
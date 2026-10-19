from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Order, OrderItem, Product


# Tests do not run collectstatic, so use plain static storage here (tests only).
PLAIN_STATIC = override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})


@PLAIN_STATIC
class AuthAndAdminAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('cust', password='Cust-pass-123')
        cls.staff = User.objects.create_user('boss', password='Boss-pass-123', is_staff=True)
        cls.product = Product.objects.create(
            name='Phone', description='d', category='Mobiles',
            price=Decimal('100.00'), gst_rate=Decimal('18.00'), stock=3,
        )

    def test_logged_out_home_redirects_to_customer_login(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith('/login/'))

    def test_customer_login_goes_to_shop(self):
        r = self.client.post('/login/', {'username': 'cust', 'password': 'Cust-pass-123'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/cart/').status_code, 200)

    def test_login_next_open_redirect_blocked(self):
        r = self.client.post('/login/?next=https://evil.example/', {'username': 'cust', 'password': 'Cust-pass-123'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)

    def test_customer_next_into_admin_ignored(self):
        r = self.client.post('/login/?next=/my-admin-dashboard/', {'username': 'cust', 'password': 'Cust-pass-123'})
        self.assertRedirects(r, '/', fetch_redirect_response=False)

    def test_invalid_login_message(self):
        r = self.client.post('/login/', {'username': 'cust', 'password': 'wrong'})
        self.assertContains(r, 'Invalid username or password.')

    def test_staff_cannot_use_customer_login(self):
        r = self.client.post('/login/', {'username': 'boss', 'password': 'Boss-pass-123'})
        self.assertContains(r, 'staff account')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_creates_plain_customer(self):
        r = self.client.post('/register/', {
            'username': 'newbie', 'email': 'n@example.com',
            'password': 'Strong-pass-123', 'confirm_password': 'Strong-pass-123',
            'is_staff': 'on', 'is_superuser': 'on',
        })
        self.assertRedirects(r, '/login/', fetch_redirect_response=False)
        u = User.objects.get(username='newbie')
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)

    def test_logout_requires_login_again(self):
        self.client.login(username='cust', password='Cust-pass-123')
        self.client.get('/logout/')
        self.assertTrue(self.client.get('/').url.startswith('/login/'))

    ADMIN_URLS = [
        'admin_dashboard', 'admin_inventory', 'admin_gst', 'admin_orders', 'admin_reports',
    ]

    def test_customer_blocked_from_admin_pages(self):
        self.client.login(username='cust', password='Cust-pass-123')
        for name in self.ADMIN_URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.assertEqual(self.client.get(reverse('admin_reports') + '?type=gst&export=csv').status_code, 403)
        # Django Admin sends customers to the single staff login, never into admin.
        r = self.client.get('/admin/', follow=True)
        self.assertEqual(r.redirect_chain[-1][0].split('?')[0], '/my-admin-login/')
        self.assertEqual(r.status_code, 200)

    def test_customer_cannot_post_stock_or_gst(self):
        self.client.login(username='cust', password='Cust-pass-123')
        self.client.post(reverse('admin_inventory'), {f'stock_{self.product.id}': '999'})
        self.client.post(reverse('admin_gst'), {'mode': 'products', f'gst_{self.product.id}': '5'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.gst_rate, Decimal('18.00'))

    def test_logged_out_admin_pages_redirect_to_admin_login(self):
        for name in self.ADMIN_URLS:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r.url.startswith('/my-admin-login/'), name)

    def test_staff_login_goes_to_dashboard_and_pages_open(self):
        r = self.client.post('/my-admin-login/', {'username': 'boss', 'password': 'Boss-pass-123'})
        self.assertRedirects(r, '/my-admin-dashboard/', fetch_redirect_response=False)
        for name in self.ADMIN_URLS:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for t in ('inventory', 'sales', 'gst'):
            self.assertEqual(self.client.get(reverse('admin_reports') + f'?type={t}').status_code, 200)
            csv_r = self.client.get(reverse('admin_reports') + f'?type={t}&export=csv')
            self.assertEqual(csv_r.status_code, 200)
            self.assertIn('text/csv', csv_r['Content-Type'])
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_customer_cannot_use_admin_login(self):
        r = self.client.post('/my-admin-login/', {'username': 'cust', 'password': 'Cust-pass-123'})
        self.assertContains(r, 'Invalid credentials or admin access denied.')

    def test_inventory_update_and_validation(self):
        self.client.login(username='boss', password='Boss-pass-123')
        self.client.post(reverse('admin_inventory'), {f'stock_{self.product.id}': '12'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)
        self.client.post(reverse('admin_inventory'), {f'stock_{self.product.id}': '-4'})
        self.client.post(reverse('admin_inventory'), {f'stock_{self.product.id}': 'abc'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)

    def test_gst_management_validation(self):
        self.client.login(username='boss', password='Boss-pass-123')
        self.client.post(reverse('admin_gst'), {'mode': 'products', f'gst_{self.product.id}': '12'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.gst_rate, Decimal('12.00'))
        self.client.post(reverse('admin_gst'), {'mode': 'products', f'gst_{self.product.id}': '150'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.gst_rate, Decimal('12.00'))


@PLAIN_STATIC
class GstAccuracyTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('boss', password='Boss-pass-123', is_staff=True)
        self.cust = User.objects.create_user('cust', password='Cust-pass-123')
        self.p = Product.objects.create(
            name='Phone', description='d', category='Mobiles',
            price=Decimal('100.00'), gst_rate=Decimal('18.00'), stock=10,
        )

    def _order(self, status='Pending', pay='COD', qty=2, rate=Decimal('18.00')):
        o = Order.objects.create(
            user=self.cust, full_name='C', phone='1', address='a', city='c', state='s',
            pincode='1', payment_method='COD', payment_status=pay, status=status,
            total_amount=self.p.price_with_gst * qty,
        )
        OrderItem.objects.create(order=o, product=self.p, quantity=qty,
                                 price=self.p.price_with_gst, gst_rate=rate)
        return o

    def test_price_with_gst_is_rounded_once(self):
        self.assertEqual(self.p.price_with_gst, Decimal('118.00'))

    def test_gst_report_not_double_counted_and_uses_saved_rate(self):
        self._order()  # 2 x 118 = 236, GST 36
        self.p.gst_rate = Decimal('5.00')  # later rate change must not alter old order
        self.p.save()
        self.client.login(username='boss', password='Boss-pass-123')
        r = self.client.get(reverse('admin_reports') + '?type=gst')
        t = r.context['totals']
        self.assertEqual(t['total'], Decimal('236.00'))
        self.assertEqual(t['taxable'], Decimal('200.00'))
        self.assertEqual(t['gst'], Decimal('36.00'))
        self.assertEqual(t['taxable'] + t['gst'], t['total'])

    def test_legacy_item_without_rate_is_flagged_estimate(self):
        o = self._order()
        OrderItem.objects.filter(order=o).update(gst_rate=None)
        self.client.login(username='boss', password='Boss-pass-123')
        r = self.client.get(reverse('admin_reports') + '?type=gst')
        self.assertEqual(r.context['legacy_rows'], 1)

    def test_cancelled_and_unpaid_excluded_from_sales_and_gst(self):
        self._order(status='Cancelled')
        self._order(pay='Pending')
        self._order()
        self.client.login(username='boss', password='Boss-pass-123')
        sales = self.client.get(reverse('admin_reports') + '?type=sales')
        self.assertEqual(sales.context['total_sales'], Decimal('236.00'))
        gst = self.client.get(reverse('admin_reports') + '?type=gst')
        self.assertEqual(len(gst.context['gst_rows']), 1)

    def test_cod_checkout_saves_gst_rate_and_reduces_stock(self):
        from .models import CartItem
        self.client.login(username='cust', password='Cust-pass-123')
        CartItem.objects.create(user=self.cust, product=self.p, quantity=2)
        r = self.client.post('/checkout/', {
            'full_name': 'C', 'phone': '999', 'address': 'a', 'city': 'c',
            'state': 's', 'pincode': '600001', 'payment_method': 'COD',
        })
        self.assertEqual(r.status_code, 200)
        item = OrderItem.objects.get()
        self.assertEqual(item.gst_rate, Decimal('18.00'))
        self.assertEqual(item.price, Decimal('118.00'))
        self.assertEqual(item.order.total_amount, Decimal('236.00'))
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 8)

    def test_dashboard_counts_match_database(self):
        Product.objects.create(name='Low', description='d', category='Books', price=1, stock=2)
        Product.objects.create(name='Out', description='d', category='Books', price=1, stock=0)
        self.client.login(username='boss', password='Boss-pass-123')
        c = self.client.get(reverse('admin_dashboard')).context
        self.assertEqual(c['total_products'], 3)
        self.assertEqual(c['total_stock_units'], 12)
        self.assertEqual(c['low_stock_count'], 1)
        self.assertEqual(c['out_of_stock_count'], 1)
        self.assertEqual(c['total_customers'], 1)

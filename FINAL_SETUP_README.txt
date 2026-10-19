CLICKNSHOP - FINAL SETUP (Windows CMD)
======================================

1. EXTRACT
   Right-click ClickNShop_Final_Ready.zip > Extract All.
   You get a folder named "clicknshop_work" (it contains manage.py).

2. COPY YOUR .env
   Copy your ORIGINAL private .env file into the clicknshop_work folder
   (the same folder as manage.py). It is not inside the ZIP on purpose.

3. OPEN CMD IN THE PROJECT FOLDER
   cd /d "PATH\TO\clicknshop_work"
   (Example: cd /d "C:\Users\ASUS\Downloads\clicknshop_work")

4. APPLY THE ONE NEW MIGRATION (REQUIRED - safe, keeps all your data)
   It only adds one empty column (OrderItem.gst_rate) so the GST report
   uses the rate each order was bought at.
   "C:\Users\ASUS\CSC project\ClickNShop\venv\Scripts\python.exe" manage.py migrate

5. CHECK
   "C:\Users\ASUS\CSC project\ClickNShop\venv\Scripts\python.exe" manage.py check

6. (OPTIONAL) RUN THE AUTOMATED TESTS
   "C:\Users\ASUS\CSC project\ClickNShop\venv\Scripts\python.exe" manage.py test
   (Uses a temporary test database; your real data is not touched.)

7. START THE SERVER
   "C:\Users\ASUS\CSC project\ClickNShop\venv\Scripts\python.exe" manage.py runserver

8. OPEN IN BROWSER
   Customer website : http://127.0.0.1:8000/          (goes to customer login)
   Customer sign-up : http://127.0.0.1:8000/register/
   Admin login      : http://127.0.0.1:8000/my-admin-login/
                      (http://127.0.0.1:8000/admin/ sends you here too)
   Admin dashboard  : http://127.0.0.1:8000/my-admin-dashboard/  (after admin login)

9. ADMIN ACCOUNT
   Use your existing staff/superuser account. Only if none works, create one
   (you choose the username and password when asked):
   "C:\Users\ASUS\CSC project\ClickNShop\venv\Scripts\python.exe" manage.py createsuperuser

DEMO TIPS
- Admin menu: Dashboard, Inventory (edit stock), GST (edit rates), Orders,
  Reports (Inventory / Sales / GST, each with "Download CSV"), Products
  (add / edit / delete in Django Admin).
- Staff accounts that are NOT superusers need product/order permissions
  (set in /admin/ > Users) to use the "Products" page. Superusers can do everything.
- Customers log in at /login/. Staff accounts are told to use the Admin Login.

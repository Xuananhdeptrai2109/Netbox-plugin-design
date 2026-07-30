# Lệnh trên terminal về backend python

- pip install django: tải django
- django-admin startproject name: khởi tạo app mới
- cd name
- python manage.py makemigrations : dùng sau khi tạo các models
- python manage.py migrate: khởi tạo accs file cần dùng
- python manage.py runserver: tạo server ảo (ví dụ cổng 8888)
- python manage.py createsuperuser: tạo tk user
- python manage.py runserver: chạy server
- cd ..(quay về thư mục trước); cd name(quay về thư mục con)
- python manage.py startapp name: tạo module
- Bấm vô settings.py để ghi thêm module vừa đặt tên vào mục install_app
- Bấm views.py để def
- Bấm urls.py để import thư viện module

# Liên kết với DATABASE

- pip install pymysql: cài mysql
- python manage.py migrate: để lưu
  _Chú ý: nếu không chạy được thì thêm lệnh vào file *init.py*_: import pymysql
  pymysql.install_as_MySQLdb()

# App: Tạo và liên kết các app với url

- Bước 1: Tạo app bằng lệnh **python manage.py startapp** name
- Bước 2: Mở phần **views.py** của app và thêm lệnh def
- Bước 3: Mở **urls.py** của Site1 copy đường dẫn là sửa lại
- Bước 4: Vô **settings.py** để thêm vô **INSTALLAPP** là 'app'
- Bước 5: Vô lại **urls.py** của Site1 và thêm đường dẫn của app

# Docker: Những lệnh chạy docker đơn giản

- docker compose up -d: tạo và chạy các container (-d: chạy ngầm dưới nền)
- docker compose ps: xem các container, cổng đang chạy hoặc dừng 
- docker compose logs -f netbox: kiểm tra lỗi (ví dụ cho netbox)
- docker compose down: dừng toàn bộ dịch vụ và xóa các container đã tạo
- docket compose restart: dùng khi vừa thay đổi bất cứ cái gì liên quan tới code
- docker compose stop: dừng chạy các container
- docker compose exec netbox python3 -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings'); import django; django.setup(); from django.core.management.commands.makemigrations import Command; Command().run_from_argv(['manage.py', 'makemigrations', 'provinces_manager'])"


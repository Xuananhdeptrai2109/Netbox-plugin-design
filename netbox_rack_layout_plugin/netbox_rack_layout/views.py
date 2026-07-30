from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class LayoutView(LoginRequiredMixin, View):
    """
    Trang chính của Rack Layout Manager.
    Hiển thị giao diện Canvas 2D để sắp xếp Rack và Device trên mặt bằng.
    """

    def get(self, request):
        return render(request, 'netbox_rack_layout/layout.html')

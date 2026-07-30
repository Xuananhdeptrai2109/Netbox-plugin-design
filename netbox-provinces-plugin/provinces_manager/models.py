from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

class Province(NetBoxModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return reverse('plugins:provinces_manager:province_list')


class District(NetBoxModel):
    province = models.ForeignKey(to=Province, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.province.name})"  
    def get_absolute_url(self):
        return reverse('plugins:provinces_manager:district_list')


class Ward(NetBoxModel):
    district = models.ForeignKey(to=District, on_delete=models.CASCADE, related_name='wards')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):  
        return f"{self.name}, {self.district.name}"  
    def get_absolute_url(self):
        return reverse('plugins:provinces_manager:ward_list')

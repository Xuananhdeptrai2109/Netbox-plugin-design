from setuptools import setup, find_packages

setup(
    name='provinces_manager',
    version='0.1',
    description='Quản lý về danh mục xã phường, tỉnh thành cho NetBox',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
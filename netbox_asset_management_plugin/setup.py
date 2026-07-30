from setuptools import setup, find_packages

setup(
    name='netbox_asset_management',
    version='0.1',
    description='Plugin quản lý tài sản cho NetBox',
    install_requires=['python-dateutil'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
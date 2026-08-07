from setuptools import setup, find_packages

setup(
    name='netbox-zabbix-plugin',
    version='1.0.0',
    description='NetBox Plugin for Zabbix Host Integration',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)

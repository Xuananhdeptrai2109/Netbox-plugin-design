from django.db import migrations, models
import django.core.validators
import django.db.models.deletion

# Lấy JSON encoder từ NetBox
try:
    from netbox.models.fields import CustomFieldJSONEncoder
except ImportError:
    CustomFieldJSONEncoder = None

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dcim', '0001_initial'),
    ]

    operations = [
        # 1. Tạo bảng Nhóm tài sản (AssetGroup)
        migrations.CreateModel(
            name='AssetGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=CustomFieldJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': 'Nhóm tài sản',
                'verbose_name_plural': 'Nhóm tài sản',
                'ordering': ['name'],
            },
        ),
        # 2. Tạo bảng Tài sản (Asset)
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=CustomFieldJSONEncoder)),
                ('name', models.CharField(max_length=100)),
                ('asset_code', models.CharField(max_length=50, unique=True)),
                ('status', models.CharField(default='active', max_length=30)),
                ('description', models.TextField(blank=True, max_length=500)),
                ('image_attachments', models.ImageField(blank=True, null=True, upload_to='plugins/netbox_asset_management/attachments/')),
                ('device_type', models.CharField(max_length=100)),
                ('model', models.CharField(max_length=100)),
                ('serial_number', models.CharField(max_length=100)),
                ('manufacturer', models.CharField(max_length=100)),
                ('installation_date', models.DateField(blank=True, null=True)),
                ('purchase_date', models.DateField(blank=True, null=True)),
                ('warranty_period', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('warranty_end', models.DateField(blank=True, editable=False, null=True)),
                # Thiết lập các Foreign Keys
                ('asset_group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assets', to='netbox_asset_management.assetgroup')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dcim.location')),
                ('parent_asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_assets', to='netbox_asset_management.asset')),
                ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dcim.region')),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dcim.site')),
            ],
            options={
                'verbose_name': 'Tài sản',
                'verbose_name_plural': 'Tài sản',
                'ordering': ('-last_updated', 'name'),
            },
        ),
    ]
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('netbox_asset_management', '0001_initial'), # Phụ thuộc vào bản 0001 đã chạy
    ]

    operations = [
        # Bổ sung các trường cho AssetGroup theo yêu cầu nghiệp vụ 
        migrations.AddField(
            model_name='assetgroup',
            name='code',
            field=models.CharField(default='TEMP_CODE', max_length=50, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='assetgroup',
            name='status',
            field=models.CharField(default='active', max_length=30),
        ),
        migrations.AddField(
            model_name='assetgroup',
            name='description',
            field=models.TextField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='assetgroup',
            name='image_attachments',
            field=models.ImageField(blank=True, null=True, upload_to='plugins/netbox_asset_management/group_attachments/'),
        ),
        migrations.AddField(
            model_name='assetgroup',
            name='exclude_from_visualization',
            field=models.BooleanField(default=False),
        ),
        # Cập nhật lại tùy chọn sắp xếp cho AssetGroup 
        migrations.AlterModelOptions(
            name='assetgroup',
            options={'ordering': ['-last_updated'], 'verbose_name': 'Nhóm tài sản', 'verbose_name_plural': 'Nhóm tài sản'},
        ),
    ]
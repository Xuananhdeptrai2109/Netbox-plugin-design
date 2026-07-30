from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_rack_layout', '0002_alter_layoutobject_layout'),
    ]

    operations = [
        migrations.AddField(
            model_name='layoutobject',
            name='width',
            field=models.FloatField(default=0, verbose_name='Chiều rộng (0 = mặc định)'),
        ),
        migrations.AddField(
            model_name='layoutobject',
            name='height',
            field=models.FloatField(default=0, verbose_name='Chiều cao (0 = mặc định)'),
        ),
    ]

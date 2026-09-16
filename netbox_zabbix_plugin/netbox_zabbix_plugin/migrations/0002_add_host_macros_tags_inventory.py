from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('netbox_zabbix_plugin', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='zabbixhostconfig',
            name='host_macros',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='zabbixhostconfig',
            name='inventory_mode',
            field=models.CharField(choices=[('disabled', 'Disabled'), ('manual', 'Manual'), ('automatic', 'Automatic')], default='disabled', max_length=20),
        ),
        migrations.AddField(
            model_name='zabbixhostconfig',
            name='custom_tags',
            field=models.JSONField(blank=True, default=list),
        ),
    ]

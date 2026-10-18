from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_product_gst_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='gst_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0001_channel_icon_and_schedule_image"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="brand",
        ),
    ]

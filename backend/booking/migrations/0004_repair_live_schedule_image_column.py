from django.db import migrations


class Migration(migrations.Migration):
    """
    Align booking_livescheduleimage with LiveScheduleImage.image (ImageField).

    Legacy DB rows used `image_url`; migration 0001 is marked applied but the
    column was never renamed. Same repair pattern as 0003 (channel.icon).
    """

    dependencies = [
        ("booking", "0003_repair_channel_icon_column"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE booking_livescheduleimage DROP COLUMN IF EXISTS image_url;",
                "ALTER TABLE booking_livescheduleimage ADD COLUMN IF NOT EXISTS image varchar(100) NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE booking_livescheduleimage DROP COLUMN IF EXISTS image;",
                "ALTER TABLE booking_livescheduleimage ADD COLUMN IF NOT EXISTS image_url varchar(500) NULL;",
            ],
            state_operations=[],
        ),
    ]

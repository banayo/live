from django.db import migrations


class Migration(migrations.Migration):
    """
    Align booking_channel schema with the current model.

    History note: an earlier deploy left the table with a `icon_url`
    column but no `icon` column even though the migration named
    `0001_channel_icon_and_schedule_image` is marked applied. This
    migration repairs the database-only difference. Django's model
    state already declares `Channel.icon`, so we pass
    `state_operations=[]` to avoid changing the migration state.
    """

    dependencies = [
        ("booking", "0002_remove_profile_brand"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE booking_channel DROP COLUMN IF EXISTS icon_url;",
                "ALTER TABLE booking_channel ADD COLUMN IF NOT EXISTS icon varchar(100) NULL;",
            ],
            reverse_sql=[
                "ALTER TABLE booking_channel DROP COLUMN IF EXISTS icon;",
                "ALTER TABLE booking_channel ADD COLUMN IF NOT EXISTS icon_url varchar(500) NULL;",
            ],
            state_operations=[],
        ),
    ]

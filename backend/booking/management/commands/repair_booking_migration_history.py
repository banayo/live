"""Mark booking.0001 as applied when DB predates booking migrations (fixes InconsistentMigrationHistory)."""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Insert django_migrations row for booking.0001_channel_icon_and_schedule_image if missing. "
        "Use when admin.* was applied before booking had any migrations (AUTH_USER_MODEL=booking.User)."
    )

    def handle(self, *args, **options):
        sql = """
        INSERT INTO django_migrations (app, name, applied)
        SELECT 'booking', '0001_channel_icon_and_schedule_image', NOW()
        WHERE NOT EXISTS (
          SELECT 1 FROM django_migrations
          WHERE app = 'booking' AND name = '0001_channel_icon_and_schedule_image'
        );
        """
        with connection.cursor() as cur:
            cur.execute(sql)
        self.stdout.write(self.style.SUCCESS("repair_booking_migration_history: done"))

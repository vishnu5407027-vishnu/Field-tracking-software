"""
Convert LocationLog into a TimescaleDB hypertable partitioned on recorded_at.

Timescale requires the partition column in every unique constraint, so the
single-column UUID primary key is widened to (id, recorded_at) first. The
whole step is a no-op on SQLite (tests) and on plain PostgreSQL without the
timescaledb extension — the table then simply stays a regular table.
"""

from django.db import migrations


def create_hypertable(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'"
        )
        if cursor.fetchone() is None:
            print("timescaledb extension not available — keeping a regular table")
            return
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        cursor.execute(
            "ALTER TABLE tracking_locationlog DROP CONSTRAINT tracking_locationlog_pkey"
        )
        cursor.execute(
            "ALTER TABLE tracking_locationlog ADD PRIMARY KEY (id, recorded_at)"
        )
        cursor.execute(
            "SELECT create_hypertable('tracking_locationlog', 'recorded_at', "
            "migrate_data => TRUE)"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tracking", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_hypertable, migrations.RunPython.noop),
    ]

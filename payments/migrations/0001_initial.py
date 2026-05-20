from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("wallet_address", models.CharField(max_length=42)),
                ("amount_eth", models.DecimalField(decimal_places=18, max_digits=24)),
                ("chain_id", models.PositiveIntegerField()),
                ("receiver_address", models.CharField(max_length=42)),
                ("match", models.CharField(blank=True, max_length=120)),
                ("pick", models.CharField(blank=True, max_length=120)),
                ("odds", models.DecimalField(decimal_places=4, default=1, max_digits=12)),
                ("tx_hash", models.CharField(blank=True, db_index=True, max_length=90)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("submitted", "Submitted"),
                            ("confirmed", "Confirmed"),
                            ("failed", "Failed"),
                        ],
                        default="created",
                        max_length=20,
                    ),
                ),
                ("failure_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

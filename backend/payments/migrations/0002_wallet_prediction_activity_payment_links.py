from django.db import migrations, models
import django.db.models.deletion


def migrate_wallets_and_predictions(apps, _schema_editor):
    Payment = apps.get_model("payments", "Payment")
    Wallet = apps.get_model("payments", "Wallet")
    Prediction = apps.get_model("payments", "Prediction")

    for payment in Payment.objects.all():
        wallet, _ = Wallet.objects.get_or_create(
            address=payment.wallet_address,
            defaults={"chain_id": payment.chain_id},
        )
        prediction = Prediction.objects.create(
            wallet=wallet,
            match=payment.match or "Unknown match",
            pick=payment.pick or "Unknown pick",
            odds=payment.odds,
            stake_eth=payment.amount_eth,
            potential_payout_eth=payment.amount_eth * payment.odds,
            status="pending",
        )
        payment.wallet = wallet
        payment.prediction = prediction
        payment.save(update_fields=["wallet", "prediction"])


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Wallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("address", models.CharField(db_index=True, max_length=42, unique=True)),
                ("wallet_name", models.CharField(blank=True, max_length=60)),
                ("chain_id", models.PositiveIntegerField(blank=True, null=True)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Prediction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("match", models.CharField(max_length=120)),
                ("pick", models.CharField(max_length=120)),
                ("odds", models.DecimalField(decimal_places=4, default=1, max_digits=12)),
                ("stake_eth", models.DecimalField(decimal_places=18, max_digits=24)),
                ("potential_payout_eth", models.DecimalField(decimal_places=18, max_digits=24)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("pending", "Pending"),
                            ("won", "Won"),
                            ("lost", "Lost"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "wallet",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="predictions", to="payments.wallet"),
                ),
            ],
        ),
        migrations.AddField(
            model_name="payment",
            name="prediction",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payments", to="payments.prediction"),
        ),
        migrations.AddField(
            model_name="payment",
            name="wallet",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="payments.wallet"),
        ),
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event",
                    models.CharField(
                        choices=[
                            ("wallet_connected", "Wallet connected"),
                            ("payment_created", "Payment created"),
                            ("payment_submitted", "Payment submitted"),
                            ("payment_confirmed", "Payment confirmed"),
                            ("payment_failed", "Payment failed"),
                        ],
                        max_length=40,
                    ),
                ),
                ("message", models.CharField(max_length=240)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "payment",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activities", to="payments.payment"),
                ),
                (
                    "prediction",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activities", to="payments.prediction"),
                ),
                (
                    "wallet",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activities", to="payments.wallet"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(migrate_wallets_and_predictions, migrations.RunPython.noop),
    ]

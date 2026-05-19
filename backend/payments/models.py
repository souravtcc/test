from django.db import models


class Wallet(models.Model):
    address = models.CharField(max_length=42, unique=True, db_index=True)
    wallet_name = models.CharField(max_length=60, blank=True)
    chain_id = models.PositiveIntegerField(null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.address


class Prediction(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING = "pending", "Pending"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        CANCELLED = "cancelled", "Cancelled"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="predictions")
    match = models.CharField(max_length=120)
    pick = models.CharField(max_length=120)
    odds = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    stake_eth = models.DecimalField(max_digits=24, decimal_places=18)
    potential_payout_eth = models.DecimalField(max_digits=24, decimal_places=18)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.match} {self.pick} {self.stake_eth} ETH"


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        SUBMITTED = "submitted", "Submitted"
        CONFIRMED = "confirmed", "Confirmed"
        FAILED = "failed", "Failed"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="payments", null=True, blank=True)
    prediction = models.ForeignKey(Prediction, on_delete=models.SET_NULL, related_name="payments", null=True, blank=True)
    wallet_address = models.CharField(max_length=42)
    amount_eth = models.DecimalField(max_digits=24, decimal_places=18)
    chain_id = models.PositiveIntegerField()
    receiver_address = models.CharField(max_length=42)
    match = models.CharField(max_length=120, blank=True)
    pick = models.CharField(max_length=120, blank=True)
    odds = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    tx_hash = models.CharField(max_length=90, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.wallet_address} {self.amount_eth} ETH {self.status}"


class Activity(models.Model):
    class Event(models.TextChoices):
        WALLET_CONNECTED = "wallet_connected", "Wallet connected"
        PAYMENT_CREATED = "payment_created", "Payment created"
        PAYMENT_SUBMITTED = "payment_submitted", "Payment submitted"
        PAYMENT_CONFIRMED = "payment_confirmed", "Payment confirmed"
        PAYMENT_FAILED = "payment_failed", "Payment failed"

    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, related_name="activities", null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, related_name="activities", null=True, blank=True)
    prediction = models.ForeignKey(Prediction, on_delete=models.SET_NULL, related_name="activities", null=True, blank=True)
    event = models.CharField(max_length=40, choices=Event.choices)
    message = models.CharField(max_length=240)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message

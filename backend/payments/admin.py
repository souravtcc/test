from django.contrib import admin

from .models import Activity, Payment, Prediction, Wallet


class PredictionInline(admin.TabularInline):
    model = Prediction
    extra = 0
    fields = ("match", "pick", "token_symbol", "odds", "stake_eth", "potential_payout_eth", "status", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("token_symbol", "amount_eth", "receiver_address", "tx_hash", "status", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("address", "wallet_name", "chain_id", "payment_count", "prediction_count", "first_seen_at", "last_seen_at")
    search_fields = ("address", "wallet_name")
    list_filter = ("chain_id", "first_seen_at", "last_seen_at")
    readonly_fields = ("first_seen_at", "last_seen_at")
    inlines = (PredictionInline, PaymentInline)

    @admin.display(description="Payments")
    def payment_count(self, obj):
        return obj.payments.count()

    @admin.display(description="Predictions")
    def prediction_count(self, obj):
        return obj.predictions.count()


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet_short", "match", "pick", "token_symbol", "odds", "stake_eth", "potential_payout_eth", "status", "created_at")
    list_filter = ("status", "match", "created_at", "updated_at")
    search_fields = ("wallet__address", "match", "pick")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("wallet",)
    list_select_related = ("wallet",)
    date_hierarchy = "created_at"

    @admin.display(description="Wallet")
    def wallet_short(self, obj):
        return f"{obj.wallet.address[:6]}...{obj.wallet.address[-4:]}"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet_short", "token_symbol", "amount_eth", "potential_payout_display", "receiver_short", "match", "pick", "odds", "status", "tx_short", "created_at")
    list_filter = ("status", "chain_id", "match", "created_at", "updated_at")
    search_fields = ("wallet_address", "receiver_address", "tx_hash", "match", "pick")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("wallet", "prediction")
    list_select_related = ("wallet", "prediction")
    date_hierarchy = "created_at"

    @admin.display(description="Wallet")
    def wallet_short(self, obj):
        address = obj.wallet_address or (obj.wallet.address if obj.wallet else "")
        return f"{address[:6]}...{address[-4:]}" if address else "-"

    @admin.display(description="Receiver")
    def receiver_short(self, obj):
        return f"{obj.receiver_address[:6]}...{obj.receiver_address[-4:]}"

    @admin.display(description="Potential payout")
    def potential_payout_display(self, obj):
        if not obj.prediction:
            return "-"
        return f"{obj.prediction.potential_payout_eth} {obj.token_symbol}"

    @admin.display(description="Tx")
    def tx_short(self, obj):
        return f"{obj.tx_hash[:10]}...{obj.tx_hash[-8:]}" if obj.tx_hash else "-"


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "wallet_short", "message", "created_at")
    list_filter = ("event", "created_at")
    search_fields = ("message", "wallet__address", "payment__tx_hash", "prediction__match", "prediction__pick")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("wallet", "payment", "prediction")
    list_select_related = ("wallet", "payment", "prediction")
    date_hierarchy = "created_at"

    @admin.display(description="Wallet")
    def wallet_short(self, obj):
        if not obj.wallet:
            return "-"
        return f"{obj.wallet.address[:6]}...{obj.wallet.address[-4:]}"

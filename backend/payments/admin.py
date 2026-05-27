import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

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
    list_display = (
        "id",
        "wallet_short",
        "match",
        "pick",
        "token_symbol",
        "odds",
        "stake_eth",
        "potential_payout_eth",
        "status",
        "payout_status",
        "payout_tx_short",
        "payout_marked_at",
        "created_at",
    )
    list_filter = ("status", "payout_status", "token_symbol", "match", "created_at", "updated_at", "payout_marked_at")
    search_fields = ("wallet__address", "match", "pick")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("wallet",)
    list_select_related = ("wallet",)
    date_hierarchy = "created_at"
    actions = (
        "mark_payout_pending",
        "mark_payout_processing",
        "mark_payout_paid",
        "mark_payout_hold",
        "reset_payout_tracking",
        "export_predictions_csv",
    )

    @admin.display(description="Wallet")
    def wallet_short(self, obj):
        return f"{obj.wallet.address[:6]}...{obj.wallet.address[-4:]}"

    @admin.display(description="Payout Tx")
    def payout_tx_short(self, obj):
        return f"{obj.payout_tx_hash[:10]}...{obj.payout_tx_hash[-8:]}" if obj.payout_tx_hash else "-"

    @admin.action(description="Payout: mark pending")
    def mark_payout_pending(self, request, queryset):
        updated = queryset.update(
            payout_status=Prediction.PayoutStatus.PENDING,
            payout_marked_at=timezone.now(),
        )
        self.message_user(request, f"{updated} prediction(s) marked as payout pending.")

    @admin.action(description="Payout: mark processing")
    def mark_payout_processing(self, request, queryset):
        updated = queryset.update(
            payout_status=Prediction.PayoutStatus.PROCESSING,
            payout_marked_at=timezone.now(),
        )
        self.message_user(request, f"{updated} prediction(s) marked as payout processing.")

    @admin.action(description="Payout: mark paid")
    def mark_payout_paid(self, request, queryset):
        updated = queryset.update(
            payout_status=Prediction.PayoutStatus.PAID,
            payout_marked_at=timezone.now(),
        )
        self.message_user(request, f"{updated} prediction(s) marked as paid.")

    @admin.action(description="Payout: mark hold")
    def mark_payout_hold(self, request, queryset):
        updated = queryset.update(
            payout_status=Prediction.PayoutStatus.HOLD,
            payout_marked_at=timezone.now(),
        )
        self.message_user(request, f"{updated} prediction(s) marked as on hold.")

    @admin.action(description="Payout: reset tracking")
    def reset_payout_tracking(self, request, queryset):
        updated = queryset.update(
            payout_status=Prediction.PayoutStatus.NOT_ELIGIBLE,
            payout_tx_hash="",
            payout_amount_eth=None,
            payout_marked_at=None,
            payout_note="",
        )
        self.message_user(request, f"{updated} prediction(s) payout tracking reset.")

    @admin.action(description="Export selected predictions as CSV")
    def export_predictions_csv(self, _request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="predictions_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "id",
            "wallet_address",
            "match",
            "pick",
            "token_symbol",
            "stake_eth",
            "odds",
            "potential_payout_eth",
            "status",
            "payout_status",
            "payout_tx_hash",
            "payout_amount_eth",
            "payout_marked_at",
            "payout_note",
            "created_at",
        ])
        for item in queryset.select_related("wallet"):
            writer.writerow([
                item.id,
                item.wallet.address,
                item.match,
                item.pick,
                item.token_symbol,
                item.stake_eth,
                item.odds,
                item.potential_payout_eth,
                item.status,
                item.payout_status,
                item.payout_tx_hash,
                item.payout_amount_eth or "",
                item.payout_marked_at.isoformat() if item.payout_marked_at else "",
                item.payout_note,
                item.created_at.isoformat(),
            ])
        return response


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

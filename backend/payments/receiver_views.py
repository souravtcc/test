import csv
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Payment, Prediction


SESSION_KEY = "receiver_dashboard_auth"
FILTER_STATUSES = ["all", *[choice[0] for choice in Prediction.PayoutStatus.choices]]


def _is_authenticated(request):
    return bool(request.session.get(SESSION_KEY))


def _dashboard_password_configured():
    return bool(settings.RECEIVER_DASHBOARD_PASSWORD)


def _predictions_queryset(request):
    payout_status = request.GET.get("payout_status", "pending")
    search = request.GET.get("q", "").strip()
    qs = Prediction.objects.select_related("wallet").order_by("-created_at")

    if payout_status not in FILTER_STATUSES:
        payout_status = "pending"
    if payout_status != "all":
        qs = qs.filter(payout_status=payout_status)
    if search:
        qs = qs.filter(wallet__address__icontains=search) | qs.filter(match__icontains=search) | qs.filter(pick__icontains=search) | qs.filter(payout_tx_hash__icontains=search)
        qs = qs.select_related("wallet").order_by("-created_at")
    return qs, payout_status, search


def _payment_lookup(predictions):
    prediction_ids = [item.id for item in predictions]
    payments = Payment.objects.filter(prediction_id__in=prediction_ids).order_by("-created_at")
    lookup = {}
    for payment in payments:
        lookup.setdefault(payment.prediction_id, payment)
    return lookup


def _export_csv(predictions):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="receiver_payouts.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "prediction_id",
        "wallet_address",
        "match",
        "pick",
        "token",
        "stake",
        "odds",
        "potential_payout",
        "prediction_status",
        "payout_status",
        "payment_tx_hash",
        "payout_tx_hash",
        "payout_amount",
        "payout_note",
        "created_at",
    ])
    payment_by_prediction = _payment_lookup(predictions)
    for item in predictions:
        payment = payment_by_prediction.get(item.id)
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
            payment.tx_hash if payment else "",
            item.payout_tx_hash,
            item.payout_amount_eth or "",
            item.payout_note,
            item.created_at.isoformat(),
        ])
    return response


def _dashboard_counts():
    return {
        "pending": Prediction.objects.filter(payout_status=Prediction.PayoutStatus.PENDING).count(),
        "processing": Prediction.objects.filter(payout_status=Prediction.PayoutStatus.PROCESSING).count(),
        "paid": Prediction.objects.filter(payout_status=Prediction.PayoutStatus.PAID).count(),
        "hold": Prediction.objects.filter(payout_status=Prediction.PayoutStatus.HOLD).count(),
        "all": Prediction.objects.count(),
    }


@require_http_methods(["GET", "POST"])
def login_view(request):
    if not _dashboard_password_configured():
        return render(request, "payments/receiver_login.html", {"not_configured": True})

    if request.method == "POST":
        password = request.POST.get("password", "")
        if password == settings.RECEIVER_DASHBOARD_PASSWORD:
            request.session[SESSION_KEY] = True
            return redirect("receiver_dashboard:dashboard")
        messages.error(request, "Invalid dashboard password.")

    return render(request, "payments/receiver_login.html", {"not_configured": False})


def logout_view(request):
    request.session.pop(SESSION_KEY, None)
    return redirect("receiver_dashboard:login")


@require_http_methods(["GET", "POST"])
def dashboard(request):
    if not _is_authenticated(request):
        return redirect(f"{reverse('receiver_dashboard:login')}?next={request.path}")

    if request.method == "POST":
        prediction_id = request.POST.get("prediction_id")
        next_status = request.POST.get("payout_status", Prediction.PayoutStatus.PENDING)
        payout_tx_hash = request.POST.get("payout_tx_hash", "").strip()
        payout_note = request.POST.get("payout_note", "").strip()[:240]
        payout_amount_raw = request.POST.get("payout_amount_eth", "").strip()

        if next_status not in [choice[0] for choice in Prediction.PayoutStatus.choices]:
            messages.error(request, "Invalid payout status.")
            return redirect("receiver_dashboard:dashboard")

        try:
            prediction = Prediction.objects.get(pk=prediction_id)
        except Prediction.DoesNotExist:
            messages.error(request, "Prediction not found.")
            return redirect("receiver_dashboard:dashboard")

        prediction.payout_status = next_status
        prediction.payout_tx_hash = payout_tx_hash
        prediction.payout_note = payout_note
        prediction.payout_marked_at = timezone.now()
        if payout_amount_raw:
            try:
                prediction.payout_amount_eth = Decimal(payout_amount_raw)
            except (InvalidOperation, TypeError):
                messages.error(request, "Invalid payout amount.")
                return redirect("receiver_dashboard:dashboard")
        elif next_status == Prediction.PayoutStatus.PAID and prediction.payout_amount_eth is None:
            prediction.payout_amount_eth = prediction.potential_payout_eth
        prediction.save(update_fields=[
            "payout_status",
            "payout_tx_hash",
            "payout_note",
            "payout_marked_at",
            "payout_amount_eth",
            "updated_at",
        ])
        messages.success(request, f"Payout tracking updated for prediction #{prediction.id}.")
        return redirect(request.POST.get("return_url") or "receiver_dashboard:dashboard")

    qs, payout_status, search = _predictions_queryset(request)
    if request.GET.get("export") == "csv":
        return _export_csv(list(qs[:1000]))

    predictions = list(qs[:200])
    payment_by_prediction = _payment_lookup(predictions)
    rows = [{"prediction": item, "payment": payment_by_prediction.get(item.id)} for item in predictions]
    return render(
        request,
        "payments/receiver_dashboard.html",
        {
            "counts": _dashboard_counts(),
            "rows": rows,
            "payout_status": payout_status,
            "search": search,
            "status_choices": Prediction.PayoutStatus.choices,
            "return_url": request.get_full_path(),
        },
    )

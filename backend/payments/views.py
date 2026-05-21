import json
import traceback
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

try:
    from web3 import Web3
except ImportError:
    Web3 = None

from .models import Activity, Payment, Prediction, Wallet


def _is_address(value):
    if Web3:
        return Web3.is_address(value)
    return isinstance(value, str) and value.startswith("0x") and len(value) == 42 and all(
        char in "0123456789abcdefABCDEF" for char in value[2:]
    )


def _checksum(value):
    if Web3:
        return Web3.to_checksum_address(value)
    return value.lower()


def _is_tx_hash(value):
    if Web3:
        return Web3.is_hex(value) and len(value) == 66
    return isinstance(value, str) and value.startswith("0x") and len(value) == 66 and all(
        char in "0123456789abcdefABCDEF" for char in value[2:]
    )


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


def _payment_json(payment):
    return {
        "id": payment.id,
        "predictionId": payment.prediction_id,
        "walletAddress": payment.wallet_address,
        "amountEth": str(payment.amount_eth),
        "chainId": payment.chain_id,
        "receiverAddress": payment.receiver_address,
        "match": payment.match,
        "pick": payment.pick,
        "odds": str(payment.odds),
        "txHash": payment.tx_hash,
        "status": payment.status,
        "failureReason": payment.failure_reason,
    }


def _wallet_json(wallet):
    return {
        "id": wallet.id,
        "address": wallet.address,
        "walletName": wallet.wallet_name,
        "chainId": wallet.chain_id,
        "firstSeenAt": wallet.first_seen_at.isoformat(),
        "lastSeenAt": wallet.last_seen_at.isoformat(),
    }


def _activity(event, message, wallet=None, payment=None, prediction=None, metadata=None):
    Activity.objects.create(
        event=event,
        message=message[:240],
        wallet=wallet,
        payment=payment,
        prediction=prediction,
        metadata=metadata or {},
    )


def _bad_request(message, status=400):
    return JsonResponse({"error": message}, status=status)


def admin_debug(request):
    if settings.DEBUG is False and request.GET.get("key") != settings.ADMIN_DEBUG_KEY:
        return _bad_request("Not found.", 404)

    path = request.GET.get("path", "/admin/payments/payment/")
    if not path.startswith("/admin/"):
        return _bad_request("Only admin paths are allowed.")

    try:
        user = get_user_model().objects.filter(is_superuser=True).order_by("id").first()
        if not user:
            return _bad_request("No superuser exists.", 500)
        client = Client(raise_request_exception=True, HTTP_HOST=request.get_host())
        client.force_login(user)
        response = client.get(path)
        return JsonResponse({"ok": True, "status": response.status_code})
    except Exception:
        return JsonResponse(
            {"ok": False, "traceback": traceback.format_exc()},
            status=500,
        )


def _verify_on_chain(payment):
    if Web3 is None:
        payment.status = Payment.Status.SUBMITTED
        payment.failure_reason = "web3 is not installed, so confirmation is pending."
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        return

    if not settings.RPC_URL:
        payment.status = Payment.Status.SUBMITTED
        payment.failure_reason = "RPC_URL is not configured, so confirmation is pending."
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        return

    web3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
    receipt = web3.eth.get_transaction_receipt(payment.tx_hash)
    tx = web3.eth.get_transaction(payment.tx_hash)

    required_wei = web3.to_wei(payment.amount_eth, "ether")
    receiver = Web3.to_checksum_address(payment.receiver_address)
    sender = Web3.to_checksum_address(payment.wallet_address)
    confirmations = max(0, web3.eth.block_number - receipt.blockNumber)

    errors = []
    if receipt.status != 1:
        errors.append("Transaction reverted.")
    if tx.get("to") != receiver:
        errors.append("Receiver address does not match.")
    if tx.get("from") != sender:
        errors.append("Sender wallet does not match.")
    if int(tx.get("value", 0)) < required_wei:
        errors.append("Transaction value is lower than expected.")
    if confirmations < settings.CONFIRMATION_BLOCKS:
        payment.status = Payment.Status.SUBMITTED
        payment.failure_reason = f"Waiting for {settings.CONFIRMATION_BLOCKS} confirmation(s)."
        payment.save(update_fields=["status", "failure_reason", "updated_at"])
        return

    if errors:
        payment.status = Payment.Status.FAILED
        payment.failure_reason = " ".join(errors)
        if payment.prediction:
            payment.prediction.status = Prediction.Status.CANCELLED
            payment.prediction.save(update_fields=["status", "updated_at"])
    else:
        payment.status = Payment.Status.CONFIRMED
        payment.failure_reason = ""
        if payment.prediction:
            payment.prediction.status = Prediction.Status.PENDING
            payment.prediction.save(update_fields=["status", "updated_at"])
    payment.save(update_fields=["status", "failure_reason", "updated_at"])
    _activity(
        Activity.Event.PAYMENT_FAILED if errors else Activity.Event.PAYMENT_CONFIRMED,
        f"Payment {payment.status}: {payment.amount_eth} ETH",
        wallet=payment.wallet,
        payment=payment,
        prediction=payment.prediction,
        metadata={"txHash": payment.tx_hash},
    )


def payment_config(_request):
    return JsonResponse(
        {
            "receiverAddress": settings.PAYMENT_RECEIVER_ADDRESS,
            "chainId": settings.CHAIN_ID,
            "confirmationBlocks": settings.CONFIRMATION_BLOCKS,
        }
    )


@csrf_exempt
def connect_wallet(request):
    if request.method != "POST":
        return _bad_request("POST required.", 405)

    data = _json_body(request)
    if data is None:
        return _bad_request("Invalid JSON.")

    address = data.get("walletAddress", "")
    if not _is_address(address):
        return _bad_request("Invalid wallet address.")

    wallet, _created = Wallet.objects.update_or_create(
        address=_checksum(address),
        defaults={
            "wallet_name": data.get("walletName", "")[:60],
            "chain_id": data.get("chainId") or None,
        },
    )
    _activity(
        Activity.Event.WALLET_CONNECTED,
        f"{wallet.wallet_name or 'Wallet'} connected: {wallet.address}",
        wallet=wallet,
        metadata={"chainId": wallet.chain_id},
    )
    return JsonResponse(_wallet_json(wallet))


@csrf_exempt
def create_payment(request):
    if request.method != "POST":
        return _bad_request("POST required.", 405)

    data = _json_body(request)
    if data is None:
        return _bad_request("Invalid JSON.")

    wallet_address = data.get("walletAddress", "")
    amount = data.get("amountEth", "")
    if not _is_address(wallet_address):
        return _bad_request("Invalid wallet address.")

    try:
        amount_eth = Decimal(str(amount))
    except (InvalidOperation, TypeError):
        return _bad_request("Invalid amount.")
    if amount_eth <= 0:
        return _bad_request("Amount must be greater than zero.")

    receiver = settings.PAYMENT_RECEIVER_ADDRESS
    if not _is_address(receiver):
        return _bad_request("Server receiver wallet is not configured.")

    try:
        odds = Decimal(str(data.get("odds", "1")))
    except (InvalidOperation, TypeError):
        return _bad_request("Invalid odds.")

    wallet, _created = Wallet.objects.update_or_create(
        address=_checksum(wallet_address),
        defaults={"chain_id": settings.CHAIN_ID},
    )
    prediction = Prediction.objects.create(
        wallet=wallet,
        match=data.get("match", "")[:120],
        pick=data.get("pick", "")[:120],
        odds=odds,
        stake_eth=amount_eth,
        potential_payout_eth=amount_eth * odds,
    )
    payment = Payment.objects.create(
        wallet=wallet,
        prediction=prediction,
        wallet_address=_checksum(wallet_address),
        amount_eth=amount_eth,
        chain_id=settings.CHAIN_ID,
        receiver_address=_checksum(receiver),
        match=data.get("match", "")[:120],
        pick=data.get("pick", "")[:120],
        odds=odds,
    )
    _activity(
        Activity.Event.PAYMENT_CREATED,
        f"Prediction created: {payment.match} {payment.pick} for {payment.amount_eth} ETH",
        wallet=wallet,
        payment=payment,
        prediction=prediction,
        metadata={"odds": str(odds), "potentialPayoutEth": str(prediction.potential_payout_eth)},
    )
    return JsonResponse(_payment_json(payment), status=201)


@csrf_exempt
def submit_payment(request, payment_id):
    if request.method != "POST":
        return _bad_request("POST required.", 405)

    data = _json_body(request)
    if data is None:
        return _bad_request("Invalid JSON.")

    tx_hash = data.get("txHash", "")
    if not _is_tx_hash(tx_hash):
        return _bad_request("Invalid transaction hash.")

    try:
        payment = Payment.objects.get(pk=payment_id)
    except Payment.DoesNotExist:
        return _bad_request("Payment not found.", 404)

    payment.tx_hash = tx_hash
    payment.status = Payment.Status.SUBMITTED
    payment.failure_reason = ""
    payment.save(update_fields=["tx_hash", "status", "failure_reason", "updated_at"])
    _activity(
        Activity.Event.PAYMENT_SUBMITTED,
        f"Transaction submitted: {tx_hash}",
        wallet=payment.wallet,
        payment=payment,
        prediction=payment.prediction,
        metadata={"txHash": tx_hash},
    )

    try:
        _verify_on_chain(payment)
    except Exception as exc:
        payment.failure_reason = f"Verification pending: {exc}"
        payment.save(update_fields=["failure_reason", "updated_at"])

    return JsonResponse(_payment_json(payment))


def payment_detail(_request, payment_id):
    try:
        payment = Payment.objects.get(pk=payment_id)
    except Payment.DoesNotExist:
        return _bad_request("Payment not found.", 404)

    if payment.tx_hash and payment.status == Payment.Status.SUBMITTED:
        try:
            _verify_on_chain(payment)
        except Exception as exc:
            payment.failure_reason = f"Verification pending: {exc}"
            payment.save(update_fields=["failure_reason", "updated_at"])

    return JsonResponse(_payment_json(payment))


def dashboard(request):
    wallet_address = request.GET.get("walletAddress", "")
    payments = Payment.objects.select_related("wallet", "prediction").order_by("-created_at")
    predictions = Prediction.objects.select_related("wallet").order_by("-created_at")
    activities = Activity.objects.select_related("wallet", "payment", "prediction").order_by("-created_at")

    if wallet_address:
        if not _is_address(wallet_address):
            return _bad_request("Invalid wallet address.")
        checksum = _checksum(wallet_address)
        payments = payments.filter(wallet_address=checksum)
        predictions = predictions.filter(wallet__address=checksum)
        activities = activities.filter(wallet__address=checksum)

    return JsonResponse(
        {
            "walletCount": Wallet.objects.count(),
            "paymentCount": payments.count(),
            "predictionCount": predictions.count(),
            "payments": [_payment_json(payment) for payment in payments[:50]],
            "predictions": [
                {
                    "id": prediction.id,
                    "walletAddress": prediction.wallet.address,
                    "match": prediction.match,
                    "pick": prediction.pick,
                    "odds": str(prediction.odds),
                    "stakeEth": str(prediction.stake_eth),
                    "potentialPayoutEth": str(prediction.potential_payout_eth),
                    "status": prediction.status,
                    "createdAt": prediction.created_at.isoformat(),
                }
                for prediction in predictions[:50]
            ],
            "activities": [
                {
                    "id": activity.id,
                    "event": activity.event,
                    "message": activity.message,
                    "walletAddress": activity.wallet.address if activity.wallet else "",
                    "createdAt": activity.created_at.isoformat(),
                    "metadata": activity.metadata,
                }
                for activity in activities[:50]
            ],
        }
    )

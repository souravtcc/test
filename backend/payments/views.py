import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

try:
    from web3 import Web3
except ImportError:
    Web3 = None

from .models import Activity, Payment, Prediction, Wallet
from .football import fetch_world_cup_markets


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


def _address_topic(address):
    return "0x" + "0" * 24 + address.lower().replace("0x", "")


def _hex_value(value):
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return str(value)


def _token_json(token):
    return {
        "symbol": token["symbol"],
        "address": token["address"],
        "decimals": token["decimals"],
        "minAmount": token.get("minAmount", "0"),
    }


def _supported_tokens():
    return [_token_json(token) for token in settings.PAYMENT_TOKENS]


def _selected_token(symbol=None):
    token_symbol = str(symbol or settings.PAYMENT_TOKEN_SYMBOL).strip().upper()
    if token_symbol == "ETH":
        return {
            "symbol": "ETH",
            "address": "",
            "decimals": 18,
            "minAmount": "0",
        }
    return settings.PAYMENT_TOKENS_BY_SYMBOL.get(token_symbol)


def _payment_token(payment):
    return {
        "symbol": payment.token_symbol or settings.PAYMENT_TOKEN_SYMBOL,
        "address": payment.token_address or settings.PAYMENT_TOKEN_ADDRESS,
        "decimals": payment.token_decimals or settings.PAYMENT_TOKEN_DECIMALS,
    }


def _payment_asset(payment):
    return "ETH" if (payment.token_symbol or "").upper() == "ETH" or not payment.token_address else "ERC20"


def _verify_erc20_transfer(web3, receipt, tx, payment, required_units):
    payment_token = _payment_token(payment)
    token = Web3.to_checksum_address(payment_token["address"])
    receiver = Web3.to_checksum_address(payment.receiver_address)
    sender = Web3.to_checksum_address(payment.wallet_address)
    transfer_topic = web3.keccak(text="Transfer(address,address,uint256)").hex()
    sender_topic = _address_topic(sender)
    receiver_topic = _address_topic(receiver)

    errors = []
    if Web3.to_checksum_address(tx.get("to")) != token:
        errors.append("Token contract does not match.")
    if Web3.to_checksum_address(tx.get("from")) != sender:
        errors.append("Sender wallet does not match.")

    transferred = 0
    for log in receipt.get("logs", []):
        topics = [_hex_value(topic).lower() for topic in log.get("topics", [])]
        if len(topics) < 3:
            continue
        if Web3.to_checksum_address(log.get("address")) != token:
            continue
        if topics[0] != transfer_topic.lower():
            continue
        if topics[1] != sender_topic.lower() or topics[2] != receiver_topic.lower():
            continue
        transferred += int(_hex_value(log.get("data", "0x0")), 16)

    if transferred < required_units:
        errors.append(f"{payment_token['symbol']} transfer amount is lower than expected.")
    return errors


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


def _payment_json(payment):
    payment_token = _payment_token(payment)
    return {
        "id": payment.id,
        "predictionId": payment.prediction_id,
        "walletAddress": payment.wallet_address,
        "amountEth": str(payment.amount_eth),
        "amountToken": str(payment.amount_eth),
        "chainId": payment.chain_id,
        "receiverAddress": payment.receiver_address,
        "paymentAsset": _payment_asset(payment),
        "tokenAddress": payment_token["address"],
        "tokenSymbol": payment_token["symbol"],
        "tokenDecimals": payment_token["decimals"],
        "match": payment.match,
        "pick": payment.pick,
        "odds": str(payment.odds),
        "potentialPayoutToken": str(payment.prediction.potential_payout_eth) if payment.prediction else "",
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


def _prediction_json(prediction):
    return {
        "id": prediction.id,
        "walletAddress": prediction.wallet.address,
        "match": prediction.match,
        "pick": prediction.pick,
        "tokenSymbol": prediction.token_symbol,
        "tokenAddress": prediction.token_address,
        "tokenDecimals": prediction.token_decimals,
        "odds": str(prediction.odds),
        "stakeEth": str(prediction.stake_eth),
        "stakeToken": str(prediction.stake_eth),
        "potentialPayoutEth": str(prediction.potential_payout_eth),
        "potentialPayoutToken": str(prediction.potential_payout_eth),
        "status": prediction.status,
        "createdAt": prediction.created_at.isoformat(),
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

    payment_asset = _payment_asset(payment)
    if payment_asset == "ERC20":
        required_units = int(payment.amount_eth * (Decimal(10) ** payment.token_decimals))
    else:
        required_units = web3.to_wei(payment.amount_eth, "ether")
    receiver = Web3.to_checksum_address(payment.receiver_address)
    sender = Web3.to_checksum_address(payment.wallet_address)
    confirmations = max(0, web3.eth.block_number - receipt.blockNumber)

    errors = []
    if receipt.status != 1:
        errors.append("Transaction reverted.")
    if payment_asset == "ERC20":
        errors.extend(_verify_erc20_transfer(web3, receipt, tx, payment, required_units))
    else:
        if Web3.to_checksum_address(tx.get("to")) != receiver:
            errors.append("Receiver address does not match.")
        if Web3.to_checksum_address(tx.get("from")) != sender:
            errors.append("Sender wallet does not match.")
        if int(tx.get("value", 0)) < required_units:
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
        f"Payment {payment.status}: {payment.amount_eth} {payment.token_symbol}",
        wallet=payment.wallet,
        payment=payment,
        prediction=payment.prediction,
        metadata={"txHash": payment.tx_hash, "tokenSymbol": payment.token_symbol},
    )


def payment_config(_request):
    return JsonResponse(
        {
            "receiverAddress": settings.PAYMENT_RECEIVER_ADDRESS,
            "chainId": settings.CHAIN_ID,
            "confirmationBlocks": settings.CONFIRMATION_BLOCKS,
            "paymentAsset": settings.PAYMENT_ASSET,
            "defaultPaymentSymbol": "ETH",
            "tokenAddress": settings.PAYMENT_TOKEN_ADDRESS,
            "tokenSymbol": settings.PAYMENT_TOKEN_SYMBOL,
            "tokenDecimals": settings.PAYMENT_TOKEN_DECIMALS,
            "defaultTokenSymbol": settings.PAYMENT_TOKEN_SYMBOL,
            "supportedTokens": _supported_tokens(),
        }
    )


def football_markets(_request):
    return JsonResponse(fetch_world_cup_markets())


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
    selected_token = _selected_token(data.get("tokenSymbol"))
    if selected_token and selected_token["symbol"] == "ETH":
        pass
    elif settings.PAYMENT_ASSET == "ERC20":
        if not selected_token:
            return _bad_request("Unsupported ERC20 token selected.")
        if not _is_address(selected_token["address"]):
            return _bad_request("Server ERC20 token contract is not configured.")
        min_amount = Decimal(str(selected_token.get("minAmount", "0")))
        if amount_eth < min_amount:
            return _bad_request(f"Minimum {selected_token['symbol']} bet is {min_amount}.")
    else:
        selected_token = {
            "symbol": "ETH",
            "address": "",
            "decimals": 18,
            "minAmount": "0",
        }

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
        token_symbol=selected_token["symbol"],
        token_address=_checksum(selected_token["address"]) if selected_token["address"] else "",
        token_decimals=selected_token["decimals"],
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
        token_symbol=selected_token["symbol"],
        token_address=_checksum(selected_token["address"]) if selected_token["address"] else "",
        token_decimals=selected_token["decimals"],
        match=data.get("match", "")[:120],
        pick=data.get("pick", "")[:120],
        odds=odds,
    )
    _activity(
        Activity.Event.PAYMENT_CREATED,
        f"Prediction created: {payment.match} {payment.pick} for {payment.amount_eth} {payment.token_symbol}",
        wallet=wallet,
        payment=payment,
        prediction=prediction,
        metadata={
            "odds": str(odds),
            "tokenSymbol": payment.token_symbol,
            "potentialPayoutToken": str(prediction.potential_payout_eth),
        },
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
        metadata={"txHash": tx_hash, "tokenSymbol": payment.token_symbol},
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
            "predictions": [_prediction_json(prediction) for prediction in predictions[:50]],
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

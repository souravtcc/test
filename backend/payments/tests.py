import json

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command

from config.settings import normalize_database_url, postgres_database_from_url

from .football import fixture_to_market, football_data_match_to_market
from .models import Activity, Payment, Prediction, Wallet


WALLET = "0x1111111111111111111111111111111111111111"
RECEIVER = "0x2222222222222222222222222222222222222222"
TX_HASH = "0x" + "a" * 64


class DatabaseUrlTests(TestCase):
    def test_normalize_database_url_strips_accidental_env_key_prefix(self):
        raw_url = "DATABASE_URL=postgresql://user:pass@example.com:6543/postgres"

        self.assertEqual(
            normalize_database_url(raw_url),
            "postgresql://user:pass@example.com:6543/postgres",
        )

    def test_postgres_database_from_url_uses_path_as_database_name(self):
        config = postgres_database_from_url(
            "DATABASE_URL=postgresql://user:pa%40ss@example.com:6543/postgres?sslmode=require"
        )

        self.assertEqual(config["NAME"], "postgres")
        self.assertEqual(config["USER"], "user")
        self.assertEqual(config["PASSWORD"], "pa@ss")
        self.assertEqual(config["HOST"], "example.com")
        self.assertEqual(config["PORT"], "6543")
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})


class EnsureAdminCommandTests(TestCase):
    def test_ensure_admin_creates_render_default_superuser(self):
        call_command("ensure_admin", verbosity=0)

        user = get_user_model().objects.get(username="admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("Admin@12345"))


@override_settings(PAYMENT_RECEIVER_ADDRESS=RECEIVER, CHAIN_ID=11155111, RPC_URL="")
class PaymentApiTests(TestCase):
    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_config_returns_payment_settings(self):
        response = self.client.get("/api/payments/config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["receiverAddress"], RECEIVER)
        self.assertEqual(response.json()["chainId"], 11155111)

    def test_markets_returns_world_cup_markets(self):
        response = self.client.get("/api/payments/markets/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("markets", body)
        self.assertGreaterEqual(len(body["markets"]), 1)
        self.assertIn("odds", body["markets"][0])

    def test_fixture_to_market_maps_real_api_fixture(self):
        market = fixture_to_market(
            {
                "fixture": {
                    "id": 123,
                    "date": "2026-06-11T20:00:00+00:00",
                    "venue": {"name": "Estadio Azteca"},
                    "status": {"short": "NS"},
                },
                "league": {"round": "Group Stage - 1"},
                "teams": {
                    "home": {"name": "Argentina", "code": "ARG"},
                    "away": {"name": "France", "code": "FRA"},
                },
            }
        )

        self.assertEqual(market["match"], "ARG VS FRA")
        self.assertEqual(market["stage"], "GROUP STAGE - 1")
        self.assertEqual(market["status"], "NS")
        self.assertEqual(market["isoDate"], "2026-06-11T20:00:00+00:00")

    def test_football_data_match_to_market_maps_world_cup_match(self):
        market = football_data_match_to_market(
            {
                "id": 999,
                "utcDate": "2026-06-12T00:30:00Z",
                "stage": "GROUP_STAGE",
                "status": "TIMED",
                "homeTeam": {"name": "Mexico", "shortName": "Mexico", "tla": "MEX"},
                "awayTeam": {"name": "South Africa", "shortName": "South Africa", "tla": "RSA"},
            }
        )

        self.assertEqual(market["match"], "MEX VS RSA")
        self.assertEqual(market["stage"], "GROUP STAGE")
        self.assertEqual(market["status"], "TIMED")
        self.assertEqual(market["isoDate"], "2026-06-12T00:30:00Z")

    def test_wallet_connection_upserts_wallet_and_activity(self):
        response = self.post_json(
            "/api/payments/wallets/connect/",
            {"walletAddress": WALLET, "walletName": "MetaMask", "chainId": 11155111},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Wallet.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(event=Activity.Event.WALLET_CONNECTED).count(), 1)
        self.assertEqual(response.json()["walletName"], "MetaMask")

    def test_create_payment_creates_prediction_and_payment(self):
        response = self.post_json(
            "/api/payments/create/",
            {
                "walletAddress": WALLET,
                "amountEth": "0.25",
                "match": "ARG VS FRA",
                "pick": "ARGENTINA TO WIN",
                "odds": "2.10",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Wallet.objects.count(), 1)
        self.assertEqual(Prediction.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(response.json()["receiverAddress"], RECEIVER.lower())
        self.assertEqual(response.json()["status"], Payment.Status.CREATED)

    def test_submit_payment_records_hash_and_keeps_rpc_pending(self):
        created = self.post_json(
            "/api/payments/create/",
            {
                "walletAddress": WALLET,
                "amountEth": "0.25",
                "match": "ARG VS FRA",
                "pick": "ARGENTINA TO WIN",
                "odds": "2.10",
            },
        ).json()

        response = self.post_json(f"/api/payments/{created['id']}/submit/", {"txHash": TX_HASH})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["txHash"], TX_HASH)
        self.assertEqual(body["status"], Payment.Status.SUBMITTED)
        self.assertIn("pending", body["failureReason"].lower())

    def test_dashboard_can_filter_by_wallet(self):
        self.post_json(
            "/api/payments/create/",
            {
                "walletAddress": WALLET,
                "amountEth": "0.25",
                "match": "ARG VS FRA",
                "pick": "ARGENTINA TO WIN",
                "odds": "2.10",
            },
        )

        response = self.client.get(f"/api/payments/dashboard/?walletAddress={WALLET}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["walletCount"], 1)
        self.assertEqual(body["paymentCount"], 1)
        self.assertEqual(body["predictionCount"], 1)

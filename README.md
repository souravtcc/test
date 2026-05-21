# FWC26 Dapp Payments

Django + React wallet betting app for FIFA World Cup 2026 markets. The backend verifies wallet payments and serves match markets; the frontend connects MetaMask, Trust Wallet, and WalletConnect.

## Local Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Use `backend/.env` for local backend config.

## Local Frontend

```powershell
cd frontend
npm install
npm run dev
```

Use `frontend/.env` for Vite frontend config.

## Required Environment

```env
DJANGO_SECRET_KEY=make_any_long_random_secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=.onrender.com,127.0.0.1,localhost
DATABASE_URL=postgresql://postgres.wxnpdkiqgenlpdgpilky:sourav%4015299@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?sslmode=require
RPC_URL=https://mainnet.infura.io/v3/e065c63298cb44ff8ba35ab232d2ab6e
CHAIN_ID=1
PAYMENT_RECEIVER_ADDRESS=0x6B3A21807fEE4f04E525DaEBcc0ceC0fCbc3bf91
CONFIRMATION_BLOCKS=1
FOOTBALL_PROVIDER=football-data
FOOTBALL_API_KEY=ee32f888beb1431b8148f281d3cdf57a
FOOTBALL_DATA_COMPETITION=WC
FOOTBALL_API_SEASON=2026
VITE_API_BASE=https://test-bjer.onrender.com/api
VITE_WALLETCONNECT_PROJECT_ID=3770f1167e86e3c5a1b4e8f323f56813
```

`CHAIN_ID=1` and the mainnet RPC URL send real ETH. Use Sepolia only for test payments.

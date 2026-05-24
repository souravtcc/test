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



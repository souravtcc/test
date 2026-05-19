# Django + React Wallet Payments

This project integrates MetaMask and Trust Wallet payments with a Django verification backend, local SQLite for development, Hostinger MySQL/MariaDB for deployment, and a React wallet UI.

## What it does

- Connects to injected wallets such as MetaMask and Trust Wallet.
- Creates a payment intent in Django before the user pays.
- Sends native chain currency from the connected wallet to your receiver wallet.
- Stores the transaction hash in Django.
- Verifies sender, receiver, amount, transaction status, and confirmations using your RPC endpoint.

## Setup

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
$env:PAYMENT_RECEIVER_ADDRESS="0xYourRealReceiverWallet"
$env:CHAIN_ID="11155111"
$env:RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
python manage.py runserver 127.0.0.1:8000
```

For Hostinger MySQL/MariaDB, set:

```powershell
$env:DB_ENGINE="mysql"
$env:MYSQL_DATABASE="your_hostinger_db_name"
$env:MYSQL_USER="your_hostinger_db_user"
$env:MYSQL_PASSWORD="your_hostinger_db_password"
$env:MYSQL_HOST="your_hostinger_mysql_host"
$env:MYSQL_PORT="3306"
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://127.0.0.1:5173`.

## Production notes

- Replace `PAYMENT_RECEIVER_ADDRESS` with a real wallet you control.
- Use a reliable RPC provider for the selected chain.
- Start on Sepolia testnet before using real funds.
- This implementation handles native currency payments. For USDT/USDC/ERC-20 payments, add token contract calls in React and verify `Transfer` logs in Django.

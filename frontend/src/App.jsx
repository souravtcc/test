import React, { useEffect, useMemo, useState } from "react";
import { ethers } from "ethers";
import EthereumProvider from "@walletconnect/ethereum-provider";

function normalizeApiBase(value) {
  const base = (value || "http://127.0.0.1:8000/api").replace(/\/+$/, "");
  return base.endsWith("/api") ? base : `${base}/api`;
}

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE);
const ERC20_ABI = [
  "function balanceOf(address owner) view returns (uint256)",
  "function transfer(address to, uint256 amount) returns (bool)",
];
const MAINNET_USDT_TOKEN = {
  symbol: "USDT",
  address: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
  decimals: 6,
  minAmount: "1",
};

const fallbackMarkets = [
  {
    match: "ARG VS FRA",
    stage: "QUARTER FINAL",
    venue: "LUSAIL STADIUM",
    time: "JUL 04 · 20:00 GST",
    isoDate: "2026-07-04T16:00:00Z",
    status: "TIMED",
    pool: "450 ETH",
    codeA: "ARG",
    teamA: "ARGENTINA",
    flagA: "🇦🇷",
    codeB: "FRA",
    teamB: "FRANCE",
    flagB: "🇫🇷",
    matchNo: "QF · M49",
    featured: true,
    bettors: "1,204",
    splitA: 54,
    splitB: 31,
    odds: [
      { label: "ARG WINS", pick: "ARGENTINA TO WIN", value: 2.1, change: "▲ 0.05" },
      { label: "DRAW", pick: "DRAW", value: 3.5, change: "—", draw: true },
      { label: "FRA WINS", pick: "FRANCE TO WIN", value: 2.4, change: "▼ 0.10", down: true },
    ],
  },
  {
    match: "BRA VS ESP",
    stage: "QUARTER FINAL",
    venue: "HARD ROCK STADIUM",
    time: "JUL 05 · 17:00 EDT",
    isoDate: "2026-07-05T21:00:00Z",
    status: "TIMED",
    pool: "380 ETH",
    codeA: "BRA",
    teamA: "BRAZIL",
    flagA: "🇧🇷",
    codeB: "ESP",
    teamB: "SPAIN",
    flagB: "🇪🇸",
    matchNo: "QF · M50",
    bettors: "978",
    splitA: 61,
    splitB: 22,
    odds: [
      { label: "BRA WINS", pick: "BRAZIL TO WIN", value: 1.8, change: "▲ 0.12" },
      { label: "DRAW", pick: "DRAW", value: 4, change: "▼ 0.20", draw: true, down: true },
      { label: "ESP WINS", pick: "SPAIN TO WIN", value: 2.9, change: "—" },
    ],
  },
  {
    match: "GER VS POR",
    stage: "QUARTER FINAL",
    venue: "ESTADIO AZTECA",
    time: "JUL 06 · 21:00 CDT",
    isoDate: "2026-07-07T02:00:00Z",
    status: "TIMED",
    pool: "290 ETH",
    codeA: "GER",
    teamA: "GERMANY",
    flagA: "🇩🇪",
    codeB: "POR",
    teamB: "PORTUGAL",
    flagB: "🇵🇹",
    matchNo: "QF · M51",
    bettors: "742",
    splitA: 47,
    splitB: 38,
    odds: [
      { label: "GER WINS", pick: "GERMANY TO WIN", value: 2.2, change: "▼ 0.08", down: true },
      { label: "DRAW", pick: "DRAW", value: 3.8, change: "▲ 0.15", draw: true },
      { label: "POR WINS", pick: "PORTUGAL TO WIN", value: 2.3, change: "—" },
    ],
  },
  {
    match: "ENG VS NED",
    stage: "QUARTER FINAL",
    venue: "METLIFE STADIUM",
    time: "JUL 07 · 20:00 EDT",
    isoDate: "2026-07-08T00:00:00Z",
    status: "TIMED",
    pool: "300 ETH",
    codeA: "ENG",
    teamA: "ENGLAND",
    flagA: "🏴",
    codeB: "NED",
    teamB: "NETHERLANDS",
    flagB: "🇳🇱",
    matchNo: "QF · M52",
    bettors: "893",
    splitA: 58,
    splitB: 28,
    odds: [
      { label: "ENG WINS", pick: "ENGLAND TO WIN", value: 1.95, change: "▼ 0.05", down: true },
      { label: "DRAW", pick: "DRAW", value: 3.6, change: "—", draw: true },
      { label: "NED WINS", pick: "NETHERLANDS TO WIN", value: 2.7, change: "▲ 0.20" },
    ],
  },
];

const leaders = [
  ["gold", "0XAA1...CC9", "+48.20 ETH", "24 WINS / 26 TOTAL"],
  ["silver", "0X22B...44D", "+31.80 ETH", "19 WINS / 22 TOTAL"],
  ["bronze", "0XFF3...009", "+22.40 ETH", "16 WINS / 20 TOTAL"],
  ["", "0X991...12A", "+18.90 ETH", "15 WINS / 18 TOTAL"],
  ["", "0X5CA...B32", "+14.60 ETH", "14 WINS / 19 TOTAL"],
];

function shorten(address) {
  if (!address) return "";
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function detectWallet(provider) {
  if (!provider) return "No wallet";
  if (provider.isTrust || provider.isTrustWallet) return "Trust Wallet";
  if (provider.isMetaMask) return "MetaMask";
  return "Injected Wallet";
}

function requestedWalletName(preferredWallet) {
  return preferredWallet === "trust" ? "Trust Wallet" : "MetaMask";
}

function walletProviderEntryProvider(entry) {
  return entry?.provider || entry;
}

function walletProviderEntryInfo(entry) {
  return entry?.provider ? entry.info || {} : {};
}

function walletProviderMatches(entry, preferredWallet) {
  const provider = walletProviderEntryProvider(entry);
  const info = walletProviderEntryInfo(entry);
  const providerName = `${info.name || ""} ${info.rdns || ""}`.toLowerCase();
  if (!provider) return false;
  if (preferredWallet === "trust") {
    return Boolean(provider.isTrust || provider.isTrustWallet || providerName.includes("trust"));
  }
  if (preferredWallet === "metamask") {
    return Boolean((provider.isMetaMask && !provider.isTrust && !provider.isTrustWallet) || providerName.includes("metamask"));
  }
  return true;
}

function findInjectedWalletProvider(ethereum, preferredWallet, discoveredProviders = []) {
  const providers = Array.isArray(ethereum?.providers) && ethereum.providers.length
    ? ethereum.providers
    : ethereum
      ? [ethereum]
      : [];
  const candidates = [...discoveredProviders, ...providers];
  const uniqueCandidates = candidates.filter((entry, index) => {
    const provider = walletProviderEntryProvider(entry);
    return provider && candidates.findIndex((candidate) => walletProviderEntryProvider(candidate) === provider) === index;
  });
  const match = uniqueCandidates.find((entry) => walletProviderMatches(entry, preferredWallet));
  return walletProviderEntryProvider(match) || null;
}

function formatDisplayAmount(value, digits = 4) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return Number(0).toFixed(digits);
  return numeric.toFixed(digits);
}

function tokenDisplayDecimals(token) {
  return token?.decimals && token.decimals < 4 ? token.decimals : 4;
}

function tokenMinAmount(token) {
  const minAmount = Number(token?.minAmount || 0);
  return Number.isFinite(minAmount) ? minAmount : 0;
}

function dashboardRowToBet(row) {
  const stake = Number(row.amountToken || row.amountEth || row.stakeToken || row.stakeEth || row.stake || 0);
  const odds = Number(row.odds || 0);
  return {
    match: row.match,
    pick: row.pick,
    odds,
    stake,
    symbol: row.tokenSymbol || row.symbol || "ETH",
    potentialPayout: Number(row.potentialPayoutToken || row.potentialPayoutEth || row.potentialPayout || stake * odds),
    status: String(row.status || "ACTIVE").toUpperCase(),
    txHash: row.txHash || "",
  };
}

function decimalPlaces(value) {
  const [, decimals = ""] = String(value || "").split(".");
  return decimals.length;
}

function currentDappUrl() {
  if (typeof window === "undefined") return "";
  return window.location.href;
}

function isMobileBrowser() {
  if (typeof navigator === "undefined") return false;
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

function walletOpenLinks() {
  const url = currentDappUrl();
  const withoutProtocol = url.replace(/^https?:\/\//, "");
  return {
    metamask: `https://metamask.app.link/dapp/${withoutProtocol}`,
    trust: `https://link.trustwallet.com/open_url?coin_id=60&url=${encodeURIComponent(url)}`,
  };
}

function chainAddParams(chainId) {
  const chains = {
    1: {
      chainName: "Ethereum Mainnet",
      nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
      rpcUrls: ["https://ethereum-rpc.publicnode.com"],
      blockExplorerUrls: ["https://etherscan.io"],
    },
  };
  const chain = chains[Number(chainId)];
  if (!chain) return null;
  return {
    chainId: `0x${Number(chainId).toString(16)}`,
    ...chain,
  };
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function estimateGasCostWei(browserProvider, txRequest) {
  const feeData = await browserProvider.getFeeData();
  const gasLimit = await browserProvider.estimateGas(txRequest);
  const gasPrice = feeData.maxFeePerGas || feeData.gasPrice;
  if (!gasPrice) return 0n;
  return gasLimit * gasPrice;
}

function formatEthForMessage(valueWei) {
  return formatDisplayAmount(ethers.formatEther(valueWei), 6);
}

async function saveWalletConnection(walletAddress, walletName, chainId) {
  try {
    await api("/payments/wallets/connect/", {
      method: "POST",
      body: JSON.stringify({ walletAddress, walletName, chainId }),
    });
  } catch {
    // Backend can be off during UI work; wallet connection should still feel responsive.
  }
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [walletAddress, setWalletAddress] = useState("");
  const [walletName, setWalletName] = useState("");
  const [walletNativeBalance, setWalletNativeBalance] = useState("");
  const [walletTokenBalances, setWalletTokenBalances] = useState({});
  const [activeProvider, setActiveProvider] = useState(null);
  const [tab, setTab] = useState("markets");
  const [bets, setBets] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [payment, setPayment] = useState(null);
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [modalMessage, setModalMessage] = useState("");
  const [toast, setToast] = useState("");
  const [block, setBlock] = useState(22041187);
  const [myBets, setMyBets] = useState([]);
  const [walletLinksOpen, setWalletLinksOpen] = useState(false);
  const [preferredMobileWallet, setPreferredMobileWallet] = useState("metamask");
  const [marketList, setMarketList] = useState(fallbackMarkets);
  const [marketSource, setMarketSource] = useState("fallback");
  const [selectedTokenSymbol, setSelectedTokenSymbol] = useState("");
  const [discoveredWalletProviders, setDiscoveredWalletProviders] = useState([]);
  const [inlineBetSlipMatch, setInlineBetSlipMatch] = useState("");

  const ethereum = typeof window !== "undefined" ? window.ethereum : null;
  const walletConnectProjectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID;
  const supportedTokens = useMemo(() => {
    const tokens = config?.supportedTokens || [];
    if (Number(config?.chainId || 1) !== 1) return tokens;
    if (tokens.some((token) => token.symbol === "USDT")) return tokens;
    return [...tokens, MAINNET_USDT_TOKEN];
  }, [config]);
  const paymentOptions = useMemo(() => {
    if (!config) return [];
    const ethOption = { symbol: "ETH", address: "", decimals: 18, minAmount: "0", native: true };
    if (config.paymentAsset !== "ERC20") return [ethOption];
    return [ethOption, ...supportedTokens.filter((token) => token.symbol !== "ETH")];
  }, [config, supportedTokens]);
  const selectedToken = paymentOptions.find((token) => token.symbol === selectedTokenSymbol) || paymentOptions[0] || null;
  const paymentSymbol = selectedToken?.symbol || config?.tokenSymbol || (config?.paymentAsset === "ERC20" ? "TOKEN" : "ETH");
  const tokenBalanceDecimals = tokenDisplayDecimals(selectedToken);
  const selectedTokenBalance = selectedToken?.native ? walletNativeBalance : selectedToken ? walletTokenBalances[selectedToken.symbol] : "";
  const selectedTokenMinAmount = tokenMinAmount(selectedToken);
  const stakePrefix = paymentSymbol;
  const totalPayout = useMemo(
    () => bets.reduce((sum, bet) => sum + (Number(bet.stake) || 0) * bet.odds, 0),
    [bets],
  );
  const validBets = useMemo(
    () => bets.map((bet) => ({ ...bet, amountEth: String(bet.stake || "").trim() })),
    [bets],
  );
  const totalStake = useMemo(
    () => validBets.reduce((sum, bet) => sum + (Number(bet.amountEth) || 0), 0),
    [validBets],
  );
  const walletTokenBalanceValue = Number(selectedTokenBalance || 0);
  const walletGasBalanceValue = Number(walletNativeBalance || 0);
  const modalBlockingMessage = useMemo(() => {
    if (!validBets.length) return "";
    const invalidBet = validBets.find((bet) => Number(bet.amountEth) <= 0);
    if (invalidBet) return "Enter an amount greater than zero for every wager.";
    if (selectedTokenMinAmount) {
      const belowMinimumBet = validBets.find((bet) => Number(bet.amountEth) < selectedTokenMinAmount);
      if (belowMinimumBet) return `Minimum ${paymentSymbol} bet is ${selectedTokenMinAmount}.`;
    }
    if (config?.paymentAsset === "ERC20" && !selectedToken?.native && walletAddress && selectedTokenBalance && walletTokenBalanceValue < totalStake) {
      return `Your wallet has ${selectedTokenBalance} ${paymentSymbol}, but this bet needs ${totalStake.toFixed(4)} ${paymentSymbol}.`;
    }
    if (walletAddress && walletNativeBalance && walletGasBalanceValue <= 0) {
      return "You need ETH in the same wallet for gas fees.";
    }
    return "";
  }, [
    config?.paymentAsset,
    paymentSymbol,
    selectedTokenBalance,
    selectedTokenMinAmount,
    totalStake,
    validBets,
    walletAddress,
    walletGasBalanceValue,
    walletNativeBalance,
    walletTokenBalanceValue,
  ]);

  useEffect(() => {
    api("/payments/config/")
      .then((data) => {
        setConfig(data);
        setSelectedTokenSymbol(data.defaultPaymentSymbol || "ETH");
      })
      .catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    if (!paymentOptions.length) return;
    if (paymentOptions.some((token) => token.symbol === selectedTokenSymbol)) return;
    setSelectedTokenSymbol(config?.defaultPaymentSymbol || paymentOptions[0].symbol);
  }, [config, paymentOptions, selectedTokenSymbol]);

  useEffect(() => {
    api("/payments/markets/")
      .then((data) => {
        if (Array.isArray(data.markets) && data.markets.length) {
          setMarketList(data.markets);
          setMarketSource(data.source || "api");
        }
      })
      .catch((error) => setMessage(`Football API unavailable: ${error.message}`));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setBlock((value) => value + 1), 12000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const handleProvider = (event) => {
      const detail = event.detail;
      if (!detail?.provider) return;
      setDiscoveredWalletProviders((current) => {
        if (current.some((entry) => entry.provider === detail.provider)) return current;
        return [...current, detail];
      });
    };
    window.addEventListener("eip6963:announceProvider", handleProvider);
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    return () => window.removeEventListener("eip6963:announceProvider", handleProvider);
  }, []);

  useEffect(() => {
    if (!ethereum?.request) return;
    ethereum.request({ method: "eth_accounts" }).then(async (accounts) => {
      if (!accounts?.[0]) return;
      const browserProvider = new ethers.BrowserProvider(ethereum);
      const network = await browserProvider.getNetwork();
      setActiveProvider(ethereum);
      setWalletAddress(accounts[0]);
      setWalletName(detectWallet(ethereum));
      await refreshWalletBalances(accounts[0], ethereum);
      saveWalletConnection(accounts[0], detectWallet(ethereum), Number(network.chainId));
    }).catch(() => {});
  }, [ethereum]);

  useEffect(() => {
    if (!activeProvider?.on) return;
    const handleAccountsChanged = async (accounts) => {
      const nextAddress = accounts?.[0] || "";
      setWalletAddress(nextAddress);
      if (nextAddress) await refreshWalletBalances(nextAddress, activeProvider);
      else {
        setWalletNativeBalance("");
        setWalletTokenBalances({});
      }
    };
    const handleChainChanged = () => {
      if (walletAddress) refreshWalletBalances(walletAddress, activeProvider);
    };
    activeProvider.on("accountsChanged", handleAccountsChanged);
    activeProvider.on("chainChanged", handleChainChanged);
    return () => {
      activeProvider.removeListener?.("accountsChanged", handleAccountsChanged);
      activeProvider.removeListener?.("chainChanged", handleChainChanged);
    };
  }, [activeProvider, walletAddress]);

  useEffect(() => {
    if (!walletAddress || !activeProvider) return;
    refreshWalletBalances(walletAddress, activeProvider);
  }, [activeProvider, selectedTokenSymbol, walletAddress]);

  useEffect(() => {
    if (!walletAddress) {
      setMyBets([]);
      return;
    }
    api(`/payments/dashboard/?walletAddress=${encodeURIComponent(walletAddress)}`)
      .then((data) => {
        const rows = Array.isArray(data.payments) && data.payments.length ? data.payments : data.predictions || [];
        setMyBets(rows.map(dashboardRowToBet));
      })
      .catch(() => {});
  }, [walletAddress]);

  function showToast(text) {
    setToast(text);
    window.setTimeout(() => setToast(""), 3500);
  }

  async function refreshWalletBalances(address, provider) {
    if (!address || !provider) return;
    try {
      const browserProvider = new ethers.BrowserProvider(provider);
      const balanceWei = await browserProvider.getBalance(address);
      setWalletNativeBalance(formatDisplayAmount(ethers.formatEther(balanceWei)));
      if (config?.paymentAsset === "ERC20" && supportedTokens.length) {
        const balances = await Promise.all(supportedTokens.map(async (token) => {
          if (!token.address) return [token.symbol, formatDisplayAmount(0, tokenDisplayDecimals(token))];
          const tokenContract = new ethers.Contract(token.address, ERC20_ABI, browserProvider);
          const tokenBalance = await tokenContract.balanceOf(address);
          return [
            token.symbol,
            formatDisplayAmount(ethers.formatUnits(tokenBalance, token.decimals || 18), tokenDisplayDecimals(token)),
          ];
        }));
        setWalletTokenBalances(Object.fromEntries(balances));
      } else {
        setWalletTokenBalances({});
      }
    } catch {
      setWalletNativeBalance("");
      setWalletTokenBalances({});
    }
  }

  function showMobileWalletLinks(preferredWallet) {
    setPreferredMobileWallet(preferredWallet);
    if (isMobileBrowser()) {
      setWalletLinksOpen(false);
      setMessage(`Opening ${requestedWalletName(preferredWallet)}...`);
      openWalletApp(preferredWallet);
      return;
    }
    setWalletLinksOpen(true);
    setMessage(`${requestedWalletName(preferredWallet)} provider not found. Open this site inside that wallet, or use WalletConnect QR.`);
  }

  function openWalletApp(wallet) {
    const links = walletOpenLinks();
    window.location.href = links[wallet];
  }

  async function connectInjectedWallet(preferredWallet) {
    const provider = findInjectedWalletProvider(window.ethereum, preferredWallet, discoveredWalletProviders);

    if (!provider) {
      showMobileWalletLinks(preferredWallet);
      return null;
    }

    try {
      const browserProvider = new ethers.BrowserProvider(provider, "any");
      const accounts = await browserProvider.send("eth_requestAccounts", []);
      if (!accounts?.[0]) throw new Error("No wallet account returned.");
      const network = await browserProvider.getNetwork();
      const connectedWalletName = detectWallet(provider);
      setActiveProvider(provider);
      setWalletAddress(accounts[0]);
      setWalletName(connectedWalletName);
      await refreshWalletBalances(accounts[0], provider);
      setWalletLinksOpen(false);
      setMessage(`${connectedWalletName} connected.`);
      saveWalletConnection(accounts[0], connectedWalletName, Number(network.chainId));
      return { address: accounts[0], provider };
    } catch (error) {
      const rawMessage = error?.shortMessage || error?.message || `${requestedWalletName(preferredWallet)} connection failed.`;
      if (error?.code === 4001 || /rejected|denied|cancel/i.test(rawMessage)) {
        setMessage(`${requestedWalletName(preferredWallet)} connection was cancelled.`);
      } else {
        setMessage(rawMessage);
      }
      return null;
    }
  }

  async function connectWalletConnect() {
    if (!walletConnectProjectId) {
      setMessage("Add VITE_WALLETCONNECT_PROJECT_ID in frontend .env to enable QR connect.");
      return null;
    }
    try {
      let activeConfig = config;
      if (!activeConfig) {
        activeConfig = await api("/payments/config/");
        setConfig(activeConfig);
        setSelectedTokenSymbol((current) => current || activeConfig.defaultPaymentSymbol || "ETH");
      }
      const chainId = Number(activeConfig?.chainId || 1);
      const provider = await EthereumProvider.init({
        projectId: walletConnectProjectId,
        chains: [chainId],
        optionalChains: [chainId],
        showQrModal: true,
      });
      await provider.enable();
      const browserProvider = new ethers.BrowserProvider(provider);
      const signer = await browserProvider.getSigner();
      const network = await browserProvider.getNetwork();
      const address = await signer.getAddress();
      setActiveProvider(provider);
      setWalletAddress(address);
      setWalletName("WalletConnect");
      await refreshWalletBalances(address, provider);
      setMessage("Wallet connected.");
      saveWalletConnection(address, "WalletConnect", Number(network.chainId));
      return { address, provider };
    } catch (error) {
      const rawMessage = error?.shortMessage || error?.message || "WalletConnect failed.";
      if (/unsupported chains|chain.*not supported/i.test(rawMessage)) {
        setMessage("Phone wallet is rejecting the requested chain. Open Ethereum Mainnet in the wallet, then scan the QR again.");
      } else {
        setMessage(rawMessage);
      }
      return null;
    }
  }

  async function ensureChain(provider = activeProvider || ethereum) {
    if (!config || !provider?.request) return;
    const current = Number(await provider.request({ method: "eth_chainId" }));
    if (current === config.chainId) return;
    const chainIdHex = `0x${Number(config.chainId).toString(16)}`;
    try {
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: chainIdHex }],
      });
    } catch (error) {
      const rawMessage = error?.shortMessage || error?.message || "";
      const needsAdd = error?.code === 4902 || /unrecognized chain|addEthereumChain|not added|unknown chain/i.test(rawMessage);
      const addParams = chainAddParams(config.chainId);
      if (!needsAdd || !addParams) throw error;
      setMessage(`Adding ${addParams.chainName} to your wallet...`);
      await provider.request({
        method: "wallet_addEthereumChain",
        params: [addParams],
      });
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: chainIdHex }],
      });
    }
  }

  function addBet(market, odd) {
    setBets((current) => {
      const existing = current.findIndex((bet) => bet.match === market.match);
      const next = { match: market.match, pick: odd.pick, odds: odd.value, stake: existing >= 0 ? current[existing].stake : "" };
      if (existing >= 0) return current.map((bet, index) => (index === existing ? next : bet));
      return [...current, next];
    });
    setInlineBetSlipMatch(market.match);
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches) {
      window.setTimeout(() => {
        const selector = `[data-betslip-match="${window.CSS?.escape ? window.CSS.escape(market.match) : market.match.replace(/"/g, '\\"')}"]`;
        document.querySelector(selector)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 80);
    }
  }

  function updateStake(index, stake) {
    setBets((current) => current.map((bet, i) => (i === index ? { ...bet, stake } : bet)));
  }

  async function payNow() {
    let unsubmittedPayment = null;
    try {
      if (!validBets.length) return;
      setModalMessage("");
      const invalidBet = validBets.find((bet) => Number(bet.amountEth) <= 0);
      if (invalidBet) throw new Error("Enter an amount greater than zero for every wager.");
      const belowMinimumBet = selectedTokenMinAmount
        ? validBets.find((bet) => Number(bet.amountEth) < selectedTokenMinAmount)
        : null;
      if (belowMinimumBet) throw new Error(`Minimum ${paymentSymbol} bet is ${selectedTokenMinAmount}.`);
      const tooManyDecimalsBet = selectedToken?.decimals
        ? validBets.find((bet) => decimalPlaces(bet.amountEth) > selectedToken.decimals)
        : null;
      if (tooManyDecimalsBet) throw new Error(`${paymentSymbol} supports up to ${selectedToken.decimals} decimal places.`);
      setStatus("working");
      setMessage(`Preparing ${validBets.length} payment${validBets.length === 1 ? "" : "s"}...`);
      setModalMessage(`Preparing ${validBets.length} payment${validBets.length === 1 ? "" : "s"}...`);

      let providerForTx = activeProvider || ethereum;
      let activeAddress = walletAddress;
      if (!activeAddress || !providerForTx) {
        setWalletLinksOpen(true);
        const connected = await connectWalletConnect();
        activeAddress = connected?.address || "";
        providerForTx = connected?.provider || providerForTx;
      }
      if (!activeAddress) throw new Error("Wallet connection is required.");
      if (!providerForTx) throw new Error("Wallet provider is not available. Use QR connect or open in a wallet browser.");
      if (config?.paymentAsset === "ERC20" && !selectedToken?.symbol) throw new Error("Choose ETH, WETH, or USDT before placing a bet.");
      await ensureChain(providerForTx);

      const browserProvider = new ethers.BrowserProvider(providerForTx);
      if (config?.paymentAsset === "ERC20" && !selectedToken?.native) {
        const requiredTokenUnits = validBets.reduce(
          (sum, bet) => sum + ethers.parseUnits(bet.amountEth, selectedToken.decimals || 18),
          0n,
        );
        const tokenContract = new ethers.Contract(selectedToken.address, ERC20_ABI, browserProvider);
        const walletTokenUnits = await tokenContract.balanceOf(activeAddress);
        if (walletTokenUnits < requiredTokenUnits) {
          throw new Error(`Insufficient ${paymentSymbol} balance for this bet.`);
        }
      }
      const gasBalanceWei = await browserProvider.getBalance(activeAddress);
      if (gasBalanceWei <= 0n) throw new Error("You need ETH in the same wallet for gas fees.");

      const signer = await browserProvider.getSigner();
      const submittedBets = [];

      for (const [index, bet] of validBets.entries()) {
        setMessage(`Creating wager ${index + 1} of ${validBets.length}: ${bet.pick}.`);
        setModalMessage(`Creating wager ${index + 1} of ${validBets.length}: ${bet.pick}.`);
        const created = await api("/payments/create/", {
          method: "POST",
          body: JSON.stringify({
            walletAddress: activeAddress,
            amountEth: bet.amountEth,
            tokenSymbol: selectedToken?.symbol,
            match: bet.match,
            pick: bet.pick,
            odds: bet.odds,
          }),
        });
        setPayment(created);
        unsubmittedPayment = created;

        setMessage(`Confirm wager ${index + 1} of ${validBets.length} in your wallet.`);
        setModalMessage(`Confirm wager ${index + 1} of ${validBets.length} in your wallet.`);
        const paymentAsset = created.paymentAsset || (selectedToken?.native ? "ETH" : config?.paymentAsset);
        const tokenDecimals = created.tokenDecimals || config?.tokenDecimals || 18;
        const paymentTokenSymbol = created.tokenSymbol || paymentSymbol;
        const stakeUnits = paymentAsset === "ERC20"
          ? ethers.parseUnits(bet.amountEth, tokenDecimals)
          : ethers.parseEther(bet.amountEth);
        if (paymentAsset !== "ERC20") {
          const nativeTransfer = {
            from: activeAddress,
            to: created.receiverAddress,
            value: stakeUnits,
          };
          const estimatedGasWei = await estimateGasCostWei(browserProvider, nativeTransfer).catch(() => 0n);
          if (gasBalanceWei < stakeUnits + estimatedGasWei) {
            const maxStakeWei = gasBalanceWei > estimatedGasWei ? gasBalanceWei - estimatedGasWei : 0n;
            throw new Error(`Insufficient ETH for stake plus gas. Balance ${formatEthForMessage(gasBalanceWei)} ETH, estimated gas ${formatEthForMessage(estimatedGasWei)} ETH. Try ${formatEthForMessage(maxStakeWei)} ETH or lower.`);
          }
        } else {
          const tokenContractForEstimate = new ethers.Contract(
            created.tokenAddress || config.tokenAddress,
            ERC20_ABI,
            signer,
          );
          const estimatedGasWei = await estimateGasCostWei(
            browserProvider,
            {
              ...(await tokenContractForEstimate.transfer.populateTransaction(created.receiverAddress, stakeUnits)),
              from: activeAddress,
            },
          ).catch(() => 0n);
          if (estimatedGasWei > 0n && gasBalanceWei < estimatedGasWei) {
            throw new Error(`Insufficient ETH for token transfer gas. Balance ${formatEthForMessage(gasBalanceWei)} ETH, estimated gas ${formatEthForMessage(estimatedGasWei)} ETH.`);
          }
        }
        const tx = paymentAsset === "ERC20"
          ? await new ethers.Contract(
            created.tokenAddress || config.tokenAddress,
            ERC20_ABI,
            signer,
          ).transfer(created.receiverAddress, stakeUnits)
          : await signer.sendTransaction({
            to: created.receiverAddress,
            value: stakeUnits,
          });
        unsubmittedPayment = null;
        await refreshWalletBalances(activeAddress, providerForTx);

        setStatus("submitted");
        setMessage(`Transaction ${index + 1} sent. Waiting for backend verification...`);
        setModalMessage(`Transaction ${index + 1} sent. Waiting for backend verification...`);
        const submitted = await api(`/payments/${created.id}/submit/`, {
          method: "POST",
          body: JSON.stringify({ txHash: tx.hash }),
        });
        setPayment(submitted);
        submittedBets.push({
          ...bet,
          stake: Number(bet.amountEth),
          status: submitted.status.toUpperCase(),
          txHash: tx.hash,
          symbol: paymentTokenSymbol,
          potentialPayout: Number(submitted.potentialPayoutToken || Number(bet.amountEth) * bet.odds),
        });
      }

      setMyBets((current) => [...submittedBets.reverse(), ...current]);
      setBets([]);
      setModalOpen(false);
      setModalMessage("");
      setMessage(`${submittedBets.length} wager${submittedBets.length === 1 ? "" : "s"} submitted on-chain.`);
      showToast(`✓  ${submittedBets.length} PREDICTION${submittedBets.length === 1 ? "" : "S"} SUBMITTED ON-CHAIN!`);
    } catch (error) {
      setStatus("failed");
      const errorMessage = error.shortMessage || error.message;
      setMessage(errorMessage);
      setModalMessage(errorMessage);
      if (unsubmittedPayment?.id) {
        try {
          const cancelled = await api(`/payments/${unsubmittedPayment.id}/cancel/`, {
            method: "POST",
            body: JSON.stringify({ reason: errorMessage }),
          });
          setPayment(cancelled);
        } catch {
          // Keep the wallet-facing error visible even if cleanup fails.
        }
      }
    }
  }

  const betSlipProps = {
    bets,
    totalPayout,
    totalStake,
    paymentSymbol,
    receiverAddress: config?.receiverAddress || "",
    supportedTokens: paymentOptions,
    selectedTokenSymbol,
    setSelectedTokenSymbol,
    walletTokenBalances: { ETH: walletNativeBalance, ...walletTokenBalances },
    selectedTokenMinAmount,
    stakePrefix,
    updateStake,
    removeBet: (index) => setBets((current) => current.filter((_, i) => i !== index)),
    clearSlip: () => {
      setBets([]);
      setInlineBetSlipMatch("");
    },
    openConfirm: () => {
      if (!bets.length) return;
      setStatus("idle");
      setModalMessage("");
      setModalOpen(true);
    },
  };

  return (
    <>
      <Ticker markets={marketList} />
      <nav>
        <div className="nav-inner">
          <div className="logo">FWC26 <span className="slash">/</span> <span>DAPP</span></div>
          <div className="nav-tabs">
            <button className={tab === "markets" ? "active" : ""} onClick={() => setTab("markets")}>LIVE MARKETS</button>
            <button className={tab === "mybets" ? "active" : ""} onClick={() => setTab("mybets")}>MY BETS <span>({bets.length + myBets.length})</span></button>
            <button className={tab === "leaderboard" ? "active" : ""} onClick={() => setTab("leaderboard")}>LEADERBOARD</button>
          </div>
          <div className="nav-right">
            <div className="stat-pill"><span>VOL</span><span className="val">1,420 ETH</span></div>
            <div className="stat-pill"><span>BLOCK</span><span className="val">{block.toLocaleString()}</span></div>
            <button className="wallet-btn" onClick={() => connectInjectedWallet("metamask")}>
              <div className="wallet-dot"></div>{walletAddress ? `${walletName} ${shorten(walletAddress)}` : "METAMASK"}
            </button>
            {walletAddress && <div className="balance-pill"><span>{paymentSymbol}</span><span className="val">{selectedTokenBalance || formatDisplayAmount(0, tokenBalanceDecimals)} {paymentSymbol}</span></div>}
            {walletAddress && <div className="balance-pill"><span>GAS</span><span className="val">{walletNativeBalance || formatDisplayAmount(0)} ETH</span></div>}
            {!walletAddress && <button className="wallet-btn trust" onClick={() => connectInjectedWallet("trust")}>TRUST</button>}
            {!walletAddress && <button className="wallet-btn qr" onClick={connectWalletConnect}>QR</button>}
          </div>
        </div>
      </nav>

      <StatusBanner message={message} status={status} walletAddress={walletAddress} walletName={walletName} />

      {walletLinksOpen && (
        <div className="wallet-fallback">
          <div>
            <div className="wallet-fallback-title">
              {preferredMobileWallet === "trust" ? "OPEN TRUST WALLET" : "OPEN METAMASK"}
            </div>
            <div className="wallet-fallback-copy">
              Mobile browser has no wallet provider. Open this same website inside your wallet app, or use WalletConnect QR.
            </div>
          </div>
          <div className="wallet-fallback-actions">
            <button className="wallet-link-btn" onClick={() => openWalletApp("metamask")}>OPEN METAMASK</button>
            <button className="wallet-link-btn trust" onClick={() => openWalletApp("trust")}>OPEN TRUST</button>
            <button className="wallet-link-btn qr" onClick={connectWalletConnect}>WALLETCONNECT QR</button>
            <button className="wallet-link-close" onClick={() => setWalletLinksOpen(false)}>CLOSE</button>
          </div>
        </div>
      )}

      <HeroStats />

      <div className="layout">
        <main>
          {tab === "markets" && (
            <LiveMarkets
              markets={marketList}
              source={marketSource}
              bets={bets}
              onAddBet={addBet}
              inlineBetSlipMatch={inlineBetSlipMatch}
              renderInlineBetSlip={() => <BetSlip {...betSlipProps} />}
            />
          )}
          {tab === "mybets" && <MyBets activeBets={bets} myBets={myBets} paymentSymbol={paymentSymbol} />}
          {tab === "leaderboard" && <Leaderboard />}
        </main>
        <aside className="sidebar">
          <div className="betslip-anchor desktop-betslip">
            <BetSlip {...betSlipProps} />
          </div>
          <LeaderboardMini />
          <ActivityFeed message={message} payment={payment} />
        </aside>
      </div>

      {modalOpen && validBets.length > 0 && (
        <div className="modal-overlay open" onClick={(event) => event.target === event.currentTarget && setModalOpen(false)}>
          <div className="modal">
            <div className="modal-header">
              <div className="modal-title">CONFIRM {validBets.length} WAGER{validBets.length === 1 ? "" : "S"}</div>
              <button className="modal-close" onClick={() => setModalOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="modal-selection-label">SELECTIONS</div>
              <div className="modal-bet-list">
                {validBets.map((bet, index) => (
                  <div className="modal-bet-row" key={`${bet.match}-${bet.pick}`}>
                    <div>
                      <div className="modal-bet-match">{bet.match}</div>
                      <div className="modal-bet-pick">{bet.pick}</div>
                    </div>
                    <div className="modal-bet-right">
                      <div>{Number(bet.amountEth || 0).toFixed(4)} {paymentSymbol}</div>
                      <div>{bet.odds.toFixed(2)}X</div>
                    </div>
                    <input className="modal-bet-input" type="number" min={selectedTokenMinAmount || 0} step={selectedTokenMinAmount || 0.001} value={bet.stake} onChange={(event) => updateStake(index, event.target.value)} />
                  </div>
                ))}
              </div>
              <div className="modal-payout">
                <div><div className="modal-payout-label">POTENTIAL PAYOUT</div><div className="modal-payout-val">{totalPayout.toFixed(4)} {paymentSymbol}</div></div>
                <div style={{ textAlign: "right" }}><div className="modal-payout-label">TOTAL STAKE</div><div className="gas-est">{totalStake.toFixed(4)} {paymentSymbol}</div></div>
              </div>
              <div className="modal-helper-copy">
                Minimum {paymentSymbol} bet is {selectedTokenMinAmount || "greater than 0"}. Receiver {config?.receiverAddress ? shorten(config.receiverAddress) : "wallet"} will receive {totalStake.toFixed(4)} {paymentSymbol}. If this bet wins, payout due is {totalPayout.toFixed(4)} {paymentSymbol}.
              </div>
              {(modalMessage || modalBlockingMessage) && (
                <div className={`modal-status ${modalMessage && status === "failed" ? "error" : ""}`}>
                  {modalMessage || modalBlockingMessage}
                </div>
              )}
              <button className="modal-confirm-btn" disabled={status === "working" || Boolean(modalBlockingMessage)} onClick={payNow}>
                <span>{status === "working" ? "CONFIRMING ON-CHAIN..." : `⚡ CONFIRM ${validBets.length} WALLET PAYMENT${validBets.length === 1 ? "" : "S"}`}</span>
                {status === "working" && <div className="spinner visible"></div>}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`toast ${toast ? "show" : ""}`}>{toast}</div>
    </>
  );
}

function Ticker({ markets }) {
  const items = ["ARG VS FRA — ARG 2.10 ▲", "BRA VS ESP — ESP 2.90 ▼", "GER VS POR — DRAW 3.80 ▲", "ENG VS NED — ENG 1.95 ▼", "TOTAL POOL: 1,420.69 ETH"];
  return <div className="ticker-bar"><div className="ticker-label">⚽ LIVE ODDS</div><div className="ticker-mask"><div className="ticker-track">{[...items, ...items, ...items].map((item, i) => <span key={`${item}-${i}`}>{item}</span>)}</div></div></div>;
}

function StatusBanner({ message, status, walletAddress, walletName }) {
  const fallback = walletAddress ? `${walletName || "Wallet"} connected: ${shorten(walletAddress)}` : "Connect wallet to place a real on-chain bet.";
  const text = message || fallback;
  const tone = status === "failed"
    ? "error"
    : status === "working" || status === "submitted"
      ? "working"
      : walletAddress
        ? "success"
        : "";
  return <div className={`top-status ${tone}`}><span className="top-status-dot"></span><span>{text}</span></div>;
}

function HeroStats() {
  return <div className="hero-wrap"><div className="hero-stats">
    <Stat label="PLATFORM VOLUME" value="1,420.69" tone="yellow" sub="ETH  ▲ 12.4% 24H" />
    <Stat label="ACTIVE MARKETS" value="08" sub="4 LIVE · 4 UPCOMING" />
    <Stat label="TOTAL BETTORS" value="3,847" tone="green" sub="UNIQUE WALLETS" />
    <Stat label="LARGEST WIN" value="48.20" tone="orange" sub="ETH  0XAA1...CC9" />
  </div></div>;
}

function Stat({ label, value, tone = "", sub }) {
  return <div className="stat-block"><div className="stat-label">{label}</div><div className={`stat-value ${tone}`}>{value}</div><div className="stat-sub">{sub}</div></div>;
}

function marketIsToday(market) {
  if (!market.isoDate) return false;
  const date = new Date(market.isoDate);
  if (Number.isNaN(date.getTime())) return false;
  return date.toDateString() === new Date().toDateString();
}

function marketIsUpcoming(market) {
  if (!market.isoDate) return true;
  const date = new Date(market.isoDate);
  if (Number.isNaN(date.getTime())) return true;
  const status = String(market.status || "").toUpperCase();
  return date.getTime() >= Date.now() && !["FT", "AET", "PEN", "FINISHED"].includes(status);
}

function LiveMarkets({ markets, source, bets, onAddBet, inlineBetSlipMatch, renderInlineBetSlip }) {
  const [filter, setFilter] = useState("all");
  const shownMarkets = markets.filter((market) => {
    if (filter === "today") return marketIsToday(market);
    if (filter === "upcoming") return marketIsUpcoming(market);
    return true;
  });
  const title = filter === "upcoming" ? "UPCOMING MARKETS" : filter === "today" ? "TODAY'S MARKETS" : "LIVE MARKETS";
  const badge = source === "fallback" ? "DEMO" : "REAL";

  return <div><div className="section-header"><div className="section-title"><div className="live-dot"></div>{title} <span className="badge">{badge}</span></div><div className="filter-tabs"><button className={`filter-tab ${filter === "all" ? "active" : ""}`} onClick={() => setFilter("all")}>ALL</button><button className={`filter-tab ${filter === "today" ? "active" : ""}`} onClick={() => setFilter("today")}>TODAY</button><button className={`filter-tab ${filter === "upcoming" ? "active" : ""}`} onClick={() => setFilter("upcoming")}>UPCOMING</button></div></div>{shownMarkets.length ? <div className="matches-grid">{shownMarkets.map((market) => <React.Fragment key={`${market.match}-${market.matchNo}`}><MatchCard market={market} bets={bets} onAddBet={onAddBet} />{inlineBetSlipMatch === market.match && <div className="mobile-betslip-slot" data-betslip-match={market.match}>{renderInlineBetSlip()}</div>}</React.Fragment>)}</div> : <div className="empty-table">NO {filter.toUpperCase()} MATCHES AVAILABLE YET.</div>}</div>;
}

function Markets({ bets, onAddBet }) {
  return <div><div className="section-header"><div className="section-title"><div className="live-dot"></div>LIVE MARKETS <span className="badge">QF</span></div><div className="filter-tabs"><button className="filter-tab active">ALL</button><button className="filter-tab">TODAY</button><button className="filter-tab">UPCOMING</button></div></div><div className="matches-grid">{fallbackMarkets.map((market) => <MatchCard key={market.match} market={market} bets={bets} onAddBet={onAddBet} />)}</div></div>;
}

function MatchCard({ market, bets, onAddBet }) {
  return <div className={`match-card ${market.featured ? "featured" : ""}`}>
    <div className="match-header"><div className="round-badge"><span className="stage">{market.stage}</span> · {market.venue}</div><div className="match-meta"><span className="match-time">{market.time}</span><span className="pool-size">POOL: <span>{market.pool}</span></span></div></div>
    <div className="match-body">
      <Team flag={market.flagA} code={market.codeA} name={market.teamA} odds={market.odds[0].value} />
      <div className="vs-section"><div className="vs-text">VS</div><div className="match-date-small">{market.matchNo}</div></div>
      <Team right flag={market.flagB} code={market.codeB} name={market.teamB} odds={market.odds[2].value} />
    </div>
    <div className="odds-row">{market.odds.map((odd) => {
      const active = bets.some((bet) => bet.match === market.match && bet.pick === odd.pick);
      return <button key={odd.pick} className={`odds-btn ${odd.draw ? "draw-btn" : ""} ${active ? "selected" : ""}`} onClick={() => onAddBet(market, odd)}><span className="odds-label">{odd.label}</span><span className="odds-val">{odd.value.toFixed(2)}X</span><span className={`odds-change ${odd.down ? "dn" : ""}`}>{odd.change}</span></button>;
    })}</div>
    <div className="match-footer"><div className="progress-bar-wrap"><div className="progress-label"><span>{market.codeA} {market.splitA}%</span><span>{market.codeB} {market.splitB}%</span></div><div className="progress-bar"><div className="progress-fill" style={{ width: `${market.splitA}%` }}></div><div className="progress-fill-right" style={{ width: `${market.splitB}%` }}></div></div></div><div className="bettors-count"><span>{market.bettors}</span> BETTORS</div></div>
  </div>;
}

function Team({ flag, code, name, odds, right = false }) {
  return <div className={`team-side ${right ? "right" : ""}`}><div className="team-flag">{flag}</div><div className="team-info"><div className="team-code">{code}</div><div className="team-full">{name}</div><div className="team-odds">{odds.toFixed(2)}x</div></div></div>;
}

function BetSlip({
  bets,
  totalPayout,
  totalStake,
  paymentSymbol,
  receiverAddress,
  supportedTokens,
  selectedTokenSymbol,
  setSelectedTokenSymbol,
  walletTokenBalances,
  selectedTokenMinAmount,
  stakePrefix,
  updateStake,
  removeBet,
  clearSlip,
  openConfirm,
}) {
  return <div className="side-panel"><div className="side-panel-header"><span className="title">BET SLIP <span className="count">{bets.length}</span></span><button className="clear-btn" onClick={clearSlip}>CLEAR ALL</button></div><div className="token-switcher"><div className="token-switcher-label">PAY WITH</div><div className="token-switcher-options">{supportedTokens.map((token) => <button key={token.symbol} className={`token-chip ${selectedTokenSymbol === token.symbol ? "active" : ""}`} onClick={() => setSelectedTokenSymbol(token.symbol)}><span>{token.symbol}</span><strong>{walletTokenBalances[token.symbol] || formatDisplayAmount(0, tokenDisplayDecimals(token))}</strong></button>)}</div><div className="token-switcher-copy">Min {selectedTokenMinAmount || "> 0"} {paymentSymbol}. Receiver {receiverAddress ? shorten(receiverAddress) : "wallet"} gets {totalStake.toFixed(4)} {paymentSymbol}. If this bet wins, payout due is {totalPayout.toFixed(4)} {paymentSymbol}.</div></div>{!bets.length ? <div className="betslip-empty"><div className="icon">🎯</div>SELECT ODDS FROM A MATCH<br />TO BUILD YOUR BET SLIP</div> : <><div>{bets.map((bet, i) => <div className="bet-item" key={`${bet.match}-${bet.pick}`}><div className="bet-item-top"><div className="bet-selection"><span className="match-name">{bet.match}</span><span className="pick">{bet.pick}</span></div><div className="bet-actions"><div className="bet-odds-badge">{bet.odds}X</div><button className="remove-bet" onClick={() => removeBet(i)}>✕</button></div></div><div className="stake-input-wrap"><div className="stake-prefix">{stakePrefix}</div><input className="stake-input" type="number" min={selectedTokenMinAmount || 0} step={selectedTokenMinAmount || 0.001} placeholder="0.00" value={bet.stake} onChange={(event) => updateStake(i, event.target.value)} /><button className="stake-max" onClick={() => updateStake(i, "1.00")}>MAX</button></div></div>)}</div><div className="betslip-footer"><div className="payout-row"><span className="payout-label">POTENTIAL PAYOUT</span><span className="payout-val">{totalPayout.toFixed(4)} {paymentSymbol}</span></div><button className="place-btn" onClick={openConfirm}><span>⚡ PLACE ALL BETS</span></button></div></>}</div>;
}

function MyBets({ activeBets, myBets, paymentSymbol }) {
  const slipBets = activeBets.map((bet) => ({
    ...bet,
    symbol: paymentSymbol,
    status: "IN SLIP",
    potentialPayout: Number(bet.stake || 0) * bet.odds,
  }));
  const renderRows = (rows, emptyText) => !rows.length
    ? <div className="empty-table">{emptyText}</div>
    : rows.map((bet, i) => <BetHistoryRow bet={bet} key={`${bet.match}-${bet.pick}-${i}`} />);

  return <div><div className="section-header"><div className="section-title">MY BETS</div></div><div className="my-bets-stack"><div className="side-panel static-panel"><div className="side-panel-header"><span className="title">ACTIVE BETS</span><span className="count">{slipBets.length}</span></div>{renderRows(slipBets, "NO ACTIVE BETS IN YOUR SLIP.")}</div><div className="side-panel static-panel"><div className="side-panel-header"><span className="title">PAST BETS</span><span className="count">{myBets.length}</span></div>{renderRows(myBets, "NO PAST BETS FOUND FOR THIS WALLET.")}</div></div></div>;
}

function BetHistoryRow({ bet }) {
  const stake = Number(bet.stake || 0);
  const odds = Number(bet.odds || 0);
  const symbol = bet.symbol || "ETH";
  return <div className="my-bet-row"><div className="my-bet-info"><div className="my-bet-match">{bet.match}</div><div className="my-bet-pick">{bet.pick} · {odds}X</div></div><div className="my-bet-right"><div className="my-bet-stake">{stake.toFixed(3)} {symbol}</div><div className="my-bet-payout">WIN PAYOUT {formatDisplayAmount(bet.potentialPayout || stake * odds, 3)} {symbol}</div><div className="status-badge pending">{bet.status}</div></div></div>;
}

function Leaderboard() {
  return <div><div className="section-header"><div className="section-title">LEADERBOARD</div></div><div className="side-panel static-panel"><div className="side-panel-header"><span>TOP PREDICTORS — FWC26</span></div>{leaders.map(([medal, addr, winnings, tag], i) => <LeaderRow key={addr} rank={i + 1} medal={medal} addr={addr} winnings={winnings} tag={tag} />)}</div></div>;
}

function LeaderboardMini() {
  return <div className="side-panel"><div className="side-panel-header"><span className="title">🏆 TOP PREDICTORS</span></div>{leaders.map(([medal, addr, winnings], i) => <LeaderRow key={addr} rank={i + 1} medal={medal} addr={addr} winnings={winnings} />)}</div>;
}

function LeaderRow({ rank, medal, addr, winnings, tag }) {
  return <div className="lb-row"><div className={`lb-rank ${medal}`}>{rank}</div><div className="lb-addr">{addr}</div><div><div className="lb-winnings">{winnings}</div>{tag && <div className="lb-tag">{tag}</div>}</div></div>;
}

function ActivityFeed({ message, payment }) {
  const rows = [
    message || "0XAB2...31C — BET 2.5 ETH → ARG WINS",
    payment?.txHash ? `${shorten(payment.txHash)} — ${payment.status.toUpperCase()}` : "0X44F...88A — BET 0.8 ETH → BRA WINS",
    "0X11D...F20 — BET 5.0 ETH → DRAW (GER/POR)",
    "0XCC9...001 — BET 1.2 ETH → ENG WINS",
  ];
  return <div className="side-panel"><div className="side-panel-header"><span className="title">🔥 RECENT ACTIVITY</span></div>{rows.map((row, i) => <div className="activity-row" key={`${row}-${i}`}><div className="activity-time">{i === 0 ? "JUST NOW" : `${i} MIN AGO`}</div><div>{row}</div></div>)}</div>;
}

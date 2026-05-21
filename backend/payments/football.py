import json
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


FALLBACK_MARKETS = [
    {
        "match": "ARG VS FRA",
        "stage": "QUARTER FINAL",
        "venue": "LUSAIL STADIUM",
        "time": "JUL 04 - 20:00 UTC",
        "pool": "450 ETH",
        "codeA": "ARG",
        "teamA": "ARGENTINA",
        "flagA": "AR",
        "codeB": "FRA",
        "teamB": "FRANCE",
        "flagB": "FR",
        "matchNo": "QF - M49",
        "isoDate": "2026-07-04T20:00:00+00:00",
        "status": "NS",
        "featured": True,
        "bettors": "1,204",
        "splitA": 54,
        "splitB": 31,
        "odds": [
            {"label": "ARG WINS", "pick": "ARGENTINA TO WIN", "value": 2.10, "change": "+0.05"},
            {"label": "DRAW", "pick": "DRAW", "value": 3.50, "change": "-", "draw": True},
            {"label": "FRA WINS", "pick": "FRANCE TO WIN", "value": 2.40, "change": "-0.10", "down": True},
        ],
    },
    {
        "match": "BRA VS ESP",
        "stage": "QUARTER FINAL",
        "venue": "HARD ROCK STADIUM",
        "time": "JUL 05 - 17:00 UTC",
        "pool": "380 ETH",
        "codeA": "BRA",
        "teamA": "BRAZIL",
        "flagA": "BR",
        "codeB": "ESP",
        "teamB": "SPAIN",
        "flagB": "ES",
        "matchNo": "QF - M50",
        "isoDate": "2026-07-05T17:00:00+00:00",
        "status": "NS",
        "featured": False,
        "bettors": "978",
        "splitA": 61,
        "splitB": 22,
        "odds": [
            {"label": "BRA WINS", "pick": "BRAZIL TO WIN", "value": 1.80, "change": "+0.12"},
            {"label": "DRAW", "pick": "DRAW", "value": 4.00, "change": "-0.20", "draw": True, "down": True},
            {"label": "ESP WINS", "pick": "SPAIN TO WIN", "value": 2.90, "change": "-"},
        ],
    },
]


def _team_code(team):
    code = (team.get("code") or "").strip().upper()
    if code:
        return code[:3]
    name = (team.get("name") or "TBA").strip().upper()
    return "".join(part[:1] for part in name.split()[:3]).ljust(3, "X")[:3]


def _format_time(value):
    if not value:
        return "TBA"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return value.upper()
    return parsed.strftime("%b %d - %H:%M UTC").upper()


def _generated_odds(seed):
    home = 1.75 + (seed % 75) / 100
    away = 1.90 + ((seed // 3) % 90) / 100
    draw = 3.10 + ((seed // 5) % 85) / 100
    return round(home, 2), round(draw, 2), round(away, 2)


def fixture_to_market(item, index=0):
    fixture = item.get("fixture") or {}
    status = fixture.get("status") or {}
    teams = item.get("teams") or {}
    league = item.get("league") or {}
    venue = fixture.get("venue") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    fixture_id = int(fixture.get("id") or index + 1)

    code_a = _team_code(home)
    code_b = _team_code(away)
    team_a = (home.get("name") or code_a).upper()
    team_b = (away.get("name") or code_b).upper()
    home_odds, draw_odds, away_odds = _generated_odds(fixture_id)
    split_a = 40 + (fixture_id % 25)
    split_b = 20 + ((fixture_id // 2) % 25)

    return {
        "match": f"{code_a} VS {code_b}",
        "stage": (league.get("round") or "FIFA WORLD CUP").upper(),
        "venue": (venue.get("name") or "TBA").upper(),
        "time": _format_time(fixture.get("date")),
        "pool": f"{100 + fixture_id % 450} ETH",
        "codeA": code_a,
        "teamA": team_a,
        "flagA": code_a[:2],
        "codeB": code_b,
        "teamB": team_b,
        "flagB": code_b[:2],
        "matchNo": f"WC - {fixture_id}",
        "isoDate": fixture.get("date") or "",
        "status": status.get("short") or "",
        "featured": index == 0,
        "bettors": f"{700 + fixture_id % 900:,}",
        "splitA": split_a,
        "splitB": split_b,
        "odds": [
            {"label": f"{code_a} WINS", "pick": f"{team_a} TO WIN", "value": home_odds, "change": "+0.04"},
            {"label": "DRAW", "pick": "DRAW", "value": draw_odds, "change": "-", "draw": True},
            {"label": f"{code_b} WINS", "pick": f"{team_b} TO WIN", "value": away_odds, "change": "-0.03", "down": True},
        ],
    }


def fetch_world_cup_markets():
    api_key = getattr(settings, "FOOTBALL_API_KEY", "")
    if not api_key:
        return {"source": "fallback", "markets": FALLBACK_MARKETS}

    query = urlencode(
        {
            "league": settings.FOOTBALL_API_LEAGUE_ID,
            "season": settings.FOOTBALL_API_SEASON,
        }
    )
    request = Request(
        f"{settings.FOOTBALL_API_BASE.rstrip('/')}/fixtures?{query}",
        headers={"x-apisports-key": api_key},
    )
    try:
        with urlopen(request, timeout=settings.FOOTBALL_API_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return {"source": "fallback", "markets": FALLBACK_MARKETS}

    markets = [fixture_to_market(item, index) for index, item in enumerate(payload.get("response", [])[:24])]
    if not markets:
        return {"source": "fallback", "markets": FALLBACK_MARKETS}
    return {"source": "api-football", "markets": markets}

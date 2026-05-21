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
    code = (team.get("code") or team.get("tla") or "").strip().upper()
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


STATIC_WORLD_CUP_FIXTURES = [
    {
        "id": 537327,
        "utcDate": "2026-06-11T19:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_A",
        "homeTeam": {"name": "Mexico", "shortName": "Mexico", "tla": "MEX"},
        "awayTeam": {"name": "South Africa", "shortName": "South Africa", "tla": "RSA"},
    },
    {
        "id": 537331,
        "utcDate": "2026-06-12T02:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_B",
        "homeTeam": {"name": "Korea Republic", "shortName": "Korea Republic", "tla": "KOR"},
        "awayTeam": {"name": "Czechia", "shortName": "Czechia", "tla": "CZE"},
    },
    {
        "id": 537332,
        "utcDate": "2026-06-12T19:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_B",
        "homeTeam": {"name": "Canada", "shortName": "Canada", "tla": "CAN"},
        "awayTeam": {"name": "Bosnia and Herzegovina", "shortName": "Bosnia-H.", "tla": "BIH"},
    },
    {
        "id": 537328,
        "utcDate": "2026-06-13T01:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_D",
        "homeTeam": {"name": "United States", "shortName": "USA", "tla": "USA"},
        "awayTeam": {"name": "Paraguay", "shortName": "Paraguay", "tla": "PAR"},
    },
    {
        "id": 537333,
        "utcDate": "2026-06-13T19:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_C",
        "homeTeam": {"name": "Qatar", "shortName": "Qatar", "tla": "QAT"},
        "awayTeam": {"name": "Switzerland", "shortName": "Switzerland", "tla": "SUI"},
    },
    {
        "id": 537334,
        "utcDate": "2026-06-13T22:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_C",
        "homeTeam": {"name": "Brazil", "shortName": "Brazil", "tla": "BRA"},
        "awayTeam": {"name": "Morocco", "shortName": "Morocco", "tla": "MAR"},
    },
    {
        "id": 537338,
        "utcDate": "2026-06-14T01:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_D",
        "homeTeam": {"name": "Haiti", "shortName": "Haiti", "tla": "HAI"},
        "awayTeam": {"name": "Scotland", "shortName": "Scotland", "tla": "SCO"},
    },
    {
        "id": 537339,
        "utcDate": "2026-06-14T04:00:00Z",
        "status": "TIMED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "GROUP_E",
        "homeTeam": {"name": "Australia", "shortName": "Australia", "tla": "AUS"},
        "awayTeam": {"name": "Turkiye", "shortName": "Turkiye", "tla": "TUR"},
    },
]


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


def football_data_match_to_market(item, index=0):
    home = item.get("homeTeam") or {}
    away = item.get("awayTeam") or {}
    fixture_id = int(item.get("id") or index + 1)
    code_a = _team_code(home)
    code_b = _team_code(away)
    team_a = (home.get("shortName") or home.get("name") or code_a).upper()
    team_b = (away.get("shortName") or away.get("name") or code_b).upper()
    home_odds, draw_odds, away_odds = _generated_odds(fixture_id)
    split_a = 40 + (fixture_id % 25)
    split_b = 20 + ((fixture_id // 2) % 25)

    return {
        "match": f"{code_a} VS {code_b}",
        "stage": (item.get("stage") or item.get("group") or "FIFA WORLD CUP").replace("_", " ").upper(),
        "venue": "TBA",
        "time": _format_time(item.get("utcDate")),
        "pool": f"{100 + fixture_id % 450} ETH",
        "codeA": code_a,
        "teamA": team_a,
        "flagA": code_a[:2],
        "codeB": code_b,
        "teamB": team_b,
        "flagB": code_b[:2],
        "matchNo": f"WC - {fixture_id}",
        "isoDate": item.get("utcDate") or "",
        "status": item.get("status") or "",
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


FALLBACK_MARKETS = [
    football_data_match_to_market(item, index)
    for index, item in enumerate(STATIC_WORLD_CUP_FIXTURES)
]


def _fetch_api_football_markets(api_key):
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
        return {"source": "world-cup-static", "markets": FALLBACK_MARKETS}

    markets = [fixture_to_market(item, index) for index, item in enumerate(payload.get("response", [])[:24])]
    if not markets:
        return {"source": "world-cup-static", "markets": FALLBACK_MARKETS}
    return {"source": "api-football", "markets": markets}


def _fetch_football_data_markets(api_key):
    query = urlencode({"season": settings.FOOTBALL_API_SEASON})
    request = Request(
        f"{settings.FOOTBALL_DATA_BASE.rstrip('/')}/competitions/{settings.FOOTBALL_DATA_COMPETITION}/matches?{query}",
        headers={"X-Auth-Token": api_key},
    )
    try:
        with urlopen(request, timeout=settings.FOOTBALL_API_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return {"source": "world-cup-static", "markets": FALLBACK_MARKETS}

    markets = [
        football_data_match_to_market(item, index)
        for index, item in enumerate(payload.get("matches", [])[:48])
    ]
    if not markets:
        return {"source": "world-cup-static", "markets": FALLBACK_MARKETS}
    return {"source": "football-data", "markets": markets}


def fetch_world_cup_markets():
    api_key = getattr(settings, "FOOTBALL_API_KEY", "")
    if not api_key:
        return {"source": "world-cup-static", "markets": FALLBACK_MARKETS}

    if settings.FOOTBALL_PROVIDER == "api-football":
        return _fetch_api_football_markets(api_key)
    return _fetch_football_data_markets(api_key)

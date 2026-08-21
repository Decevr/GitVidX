from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen
import hashlib
import html
import ipaddress
import json
import re
import socket
import ssl
import time

SSL_LOOSE = ssl._create_unverified_context()

ROOT = Path(__file__).resolve().parent
PORT = 8767
APP_UA = "GitVidX/1.3 (adult video search)"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
BLOCK = re.compile(
    r"\b("
    r"child|children|kid|kids|toddler|infant|baby|babies|minor|minors|"
    r"underage|under[\s-]?age|preteen|pre[\s-]?teen|loli|lolita|shota|"
    r"pedo|paedo|jailbait|young[\s-]?girl|little[\s-]?girl|"
    r"(1[0-7]|[0-9])\s*(yo|yr|years?\s*old)|"
    r"leak|leaked|leaks|stolen|hacked|fappening|celebgate|"
    r"revenge\s*porn|non[\s-]?consensual|without\s+consent|no\s+consent|"
    r"hidden\s*cam|spy\s*cam|voyeur|creepshot|upskirt|downblouse|"
    r"passed\s+out|unconscious|drugged|sleeping\s+nude|"
    r"rape|raped|forced|blackmail|deepnude|undress"
    r")\b",
    re.I,
)
BLOCKED_HOST_BITS = (
    "leak", "leaked", "thothub", "fappening", "celebgate", "nudel",
    "coomer", "kemono", "simpcity", "fapello", "cyberdrop",
)
BLOCK_REASON = (
    "That search is blocked. GitVidX only shows legal, consensual, 18+ videos. "
    "No leaks, hidden cameras, or non-consensual content."
)
CACHE: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 180
DAILY_Q = "__daily__"
NEW_Q = "__new__"
VIEWS_Q = "__views__"
DAILY_DIR = ROOT / ".cache"


def feed_kind(query: str) -> str:
    q = (query or "").strip().lower()
    if q in (NEW_Q, DAILY_Q):
        return "new"
    if q == VIEWS_Q:
        return "views"
    return ""


def is_daily(query: str) -> bool:
    return feed_kind(query) == "new"


def is_feed(query: str) -> bool:
    return bool(feed_kind(query))


def today_stamp() -> str:
    return date.today().isoformat()


def daily_cache_path(source: str, page: int, kind: str = "new") -> Path:
    safe = re.sub(r"[^a-z0-9]+", "-", (source or "all").lower()).strip("-") or "all"
    label = kind if kind in ("new", "views") else "new"
    return DAILY_DIR / f"feed-{label}-{today_stamp()}-{safe}-{page}.json"


def load_daily_cache(source: str, page: int, kind: str = "new") -> dict | None:
    path = daily_cache_path(source, page, kind)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("date") == today_stamp() and data.get("items"):
            return data
    except Exception:
        return None
    return None


def save_daily_cache(source: str, page: int, payload: dict, kind: str = "new") -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = today_stamp()
    for old in DAILY_DIR.glob("feed-*.json"):
        if stamp not in old.name:
            try:
                old.unlink()
            except OSError:
                pass
    for old in DAILY_DIR.glob("daily-*.json"):
        try:
            old.unlink()
        except OSError:
            pass
    daily_cache_path(source, page, kind).write_text(json.dumps(payload), encoding="utf-8")


STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "plus",
    "hair", "sex", "fuck", "video", "style", "position", "man", "guy",
    "view", "camera", "cam", "shot", "angle",
}

CATEGORY_ALIASES: dict[str, list[str]] = {
    "amateur": ["amateur", "real amateur"],
    "milf": ["milf"],
    "lesbian": ["lesbian", "lesbians", "girl on girl"],
    "blonde": ["blonde", "blond", "blonde hair", "blond hair"],
    "brunette": ["brunette", "brown hair", "brown haired"],
    "anal": ["anal"],
    "pov": ["pov", "point of view"],
    "solo": ["solo", "masturbation", "masturbating"],
    "hardcore": ["hardcore"],
    "blowjob": ["blowjob", "blow job", "bj", "cock sucking"],
    "creampie": ["creampie", "cream pie"],
    "big tits": ["big tits", "bigtits", "big boobs", "huge tits", "huge boobs", "big breasts"],
    "tan line": ["tan line", "tanline", "tan lines", "tanlines"],
    "small tits": [
        "small tits", "small tit", "tiny tits", "tiny tit", "little tits",
        "small boobs", "tiny boobs", "little boobs", "small breasts",
        "tiny breasts", "flat chest", "small chest", "petite tits", "a cup",
    ],
    "medium tits": [
        "medium tits", "medium boobs", "medium breasts", "average tits",
        "c cup", "medium sized tits",
    ],
    "large tits": [
        "large tits", "huge tits", "big tits", "giant tits", "massive tits",
        "big boobs", "huge boobs", "massive boobs", "giant boobs",
        "big breasts", "huge breasts", "large breasts", "big naturals",
        "busty", "bigtits",
    ],
    "natural tits": ["natural tits", "natural breasts", "natural boobs", "naturals", "real tits"],
    "perky tits": ["perky tits", "perky breasts", "perky boobs"],
    "large ass": [
        "large ass", "big ass", "huge ass", "fat ass", "phat ass",
        "big booty", "huge booty", "bubble butt", "big butt",
    ],
    "round ass": ["round ass", "round booty", "peach ass", "bubble butt"],
    "petite": ["petite"],
    "curvy": ["curvy", "curvy body"],
    "thick": ["thick", "thicc"],
    "pawg": ["pawg"],
    "cmnf": ["cmnf", "clothed male naked female"],
    "cfnm": ["cfnm", "clothed female naked male"],
    "lap dance": ["lap dance", "lapdance"],
    "striptease": ["striptease", "strip tease"],
    "oil": ["oiled", "oil massage", "oiled up", "oily"],
    "massage": ["massage"],
    "storyline": ["storyline", "story line", "plot"],
    "full movie": ["full movie", "full length", "feature length"],
    "full scene": ["full scene", "complete scene"],
    "asian": ["asian"],
    "latina": ["latina", "latin", "hispanic"],
    "threesome": ["threesome", "threesom", "ffm", "mmf", "3some"],
    "feet": ["feet", "foot fetish", "footjob", "soles"],
    "socks": ["socks", "sock", "sockjob", "sock fetish", "ankle socks", "white socks"],
    "cheating": ["cheating", "cheating wife", "cheats", "affair"],
    "cuckold": ["cuckold", "cuckolding", "cuck"],
    "teen": ["teen", "18 teen", "18 year", "barely 18"],
    "step-sis": ["stepsister", "step sister", "step-sister", "stepsis", "step sis", "step-sis"],
    "homemade": ["homemade", "home made", "homemade amateur", "real homemade"],
    "onlyfans": ["onlyfans", "only fans", "only-fans"],
    "ai": ["ai generated", "ai porn", "ai generated porn", "artificial intelligence"],
    "missionary": ["missionary"],
    "doggy": ["doggy", "doggy style", "doggystyle", "doggyestyle"],
    "cowgirl": ["cowgirl", "cow girl"],
    "reverse cowgirl": ["reverse cowgirl", "reversecowgirl"],
    "spooning": ["spooning", "spoon fuck"],
    "standing": ["standing sex", "standing fuck", "standing doggy"],
    "69": ["69", "sixty nine", "sixtynine"],
    "prone bone": ["prone bone", "pronebone"],
    "mating press": ["mating press", "matingpress"],
    "lotus": ["lotus position", "lotus pose"],
    "piledriver": ["piledriver", "pile driver"],
    "butterfly": ["butterfly position", "butterfly pose"],
    "amazon": ["amazon position", "amazon pose"],
    "wheelbarrow": ["wheelbarrow"],
    "anvil": ["anvil position", "anvil pose"],
    "facesitting": ["facesitting", "face sitting", "queening"],
    "scissoring": ["scissoring", "scissor"],
    "sideways": ["sideways", "side fuck", "on the side"],
    "legs up": ["legs up", "legs in the air", "legs over"],
    "bent over": ["bent over", "bend over", "bending over"],
    "full nelson": ["full nelson"],
    "against wall": ["against the wall", "wall sex", "pinned to the wall", "against wall"],
    "chair": ["chair sex", "chair fuck", "on the chair"],
    "michigan": ["michigan", "michigan sex", "michigan position"],
    "slipped in": ["slipped it in", "accidentally slipped it in", "accidentally slipped in", "accidental slip"],
    "redhead": ["redhead", "red hair", "red haired", "ginger"],
    "black hair": ["black hair", "black haired", "dark hair", "jet black hair"],
    "auburn": ["auburn", "auburn hair"],
    "platinum": ["platinum blonde", "platinum blond", "platinum hair", "platinum"],
    "grey": ["grey hair", "gray hair", "silver hair", "granny hair"],
    "pink hair": ["pink hair", "pink haired"],
    "blue hair": ["blue hair", "blue haired"],
    "purple hair": ["purple hair", "purple haired"],
    "cellphone": ["cellphone", "cell phone", "phone video", "mobile video", "iphone video"],
    "snapchat": ["snapchat", "snap chat"],
    "hotel": ["hotel sex", "hotel room", "hotel fuck"],
    "motel": ["motel sex", "motel room", "motel fuck"],
    "car": ["car sex", "car fuck", "in the car", "backseat", "back seat"],
    "public": ["public sex", "public fuck", "in public"],
    "sneaky": ["sneaky sex", "sneaky fuck", "sneaky"],
    "quickie": ["quickie", "quick fuck"],
    "tramp stamp": ["tramp stamp", "lower back tattoo"],
    "delivery guy": ["delivery guy", "delivery man", "pizza guy"],
    "maintenance man": ["maintenance man", "handyman", "repair man", "plumber"],
    "co-worker": [
        "coworker", "co worker", "co-worker", "office sex", "office fuck",
        "at work", "colleague", "coworkers",
    ],
    "babysitter": ["babysitter", "baby sitter", "baby-sitter", "nanny"],
    "cosplay": ["cosplay", "cos play", "costume play"],
    "parody": ["parody", "porn parody", "xxx parody", "spoof"],
    "fly on the wall": ["fly on the wall", "fly-on-the-wall", "third person camera"],
    "third person": ["third person", "third person view"],
    "close up": ["close up", "close-up", "closeup"],
    "full body": ["full body", "fullbody"],
    "overhead": ["overhead view", "top down", "birds eye", "bird's eye"],
    "low angle": ["low angle", "low-angle"],
    "side view": ["side view", "side angle"],
    "behind camera": ["camera from behind", "shot from behind", "from behind camera"],
    "face cam": ["face cam", "facecam"],
    "looking at camera": ["looking at camera", "looks at camera", "look at camera"],
    "mirror": ["mirror fuck", "mirror sex", "in the mirror"],
    "handheld": ["handheld camera", "handheld"],
    "tripod": ["tripod", "tripod camera"],
    "gopro": ["gopro", "go pro"],
    "selfie cam": ["selfie", "front camera", "selfie cam"],
    "two camera": ["two camera", "dual camera", "multi cam"],
    "cinematic": ["cinematic"],
    "over the shoulder": ["over the shoulder", "over-the-shoulder"],
    "wide shot": ["wide shot", "wide angle"],
}

SEARCH_PHRASE: dict[str, str] = {
    "amateur": "amateur",
    "milf": "milf",
    "lesbian": "lesbian",
    "blonde": "blonde",
    "brunette": "brunette",
    "anal": "anal",
    "pov": "pov",
    "solo": "solo",
    "hardcore": "hardcore",
    "blowjob": "blowjob",
    "creampie": "creampie",
    "big tits": "big tits",
    "tan line": "tan lines",
    "small tits": "small tits",
    "medium tits": "medium tits",
    "large tits": "huge tits",
    "natural tits": "natural tits",
    "perky tits": "perky tits",
    "large ass": "big ass",
    "round ass": "round ass",
    "petite": "petite",
    "curvy": "curvy",
    "thick": "thick",
    "pawg": "pawg",
    "cmnf": "cmnf",
    "cfnm": "cfnm",
    "lap dance": "lap dance",
    "striptease": "striptease",
    "oil": "oiled",
    "massage": "massage",
    "storyline": "storyline",
    "full movie": "full movie",
    "full scene": "full scene",
    "asian": "asian",
    "latina": "latina",
    "threesome": "threesome",
    "feet": "feet",
    "socks": "socks",
    "cheating": "cheating wife",
    "cuckold": "cuckold",
    "teen": "teen",
    "step-sis": "stepsister",
    "homemade": "homemade",
    "onlyfans": "onlyfans",
    "ai": "ai generated",
    "missionary": "missionary",
    "doggy": "doggy style",
    "cowgirl": "cowgirl",
    "reverse cowgirl": "reverse cowgirl",
    "spooning": "spooning",
    "standing": "standing sex",
    "69": "69",
    "prone bone": "prone bone",
    "mating press": "mating press",
    "lotus": "lotus position",
    "piledriver": "piledriver",
    "butterfly": "butterfly position",
    "amazon": "amazon position",
    "wheelbarrow": "wheelbarrow",
    "anvil": "anvil position",
    "facesitting": "facesitting",
    "scissoring": "scissoring",
    "sideways": "sideways fuck",
    "legs up": "legs up",
    "bent over": "bent over",
    "full nelson": "full nelson",
    "against wall": "against the wall",
    "chair": "chair sex",
    "michigan": "michigan",
    "slipped in": "slipped it in",
    "redhead": "redhead",
    "black hair": "black hair",
    "auburn": "auburn",
    "platinum": "platinum blonde",
    "grey": "grey hair",
    "pink hair": "pink hair",
    "blue hair": "blue hair",
    "purple hair": "purple hair",
    "cellphone": "cellphone video",
    "snapchat": "snapchat",
    "hotel": "hotel sex",
    "motel": "motel sex",
    "car": "car sex",
    "public": "public sex",
    "sneaky": "sneaky sex",
    "quickie": "quickie",
    "tramp stamp": "tramp stamp",
    "delivery guy": "delivery guy",
    "maintenance man": "maintenance man",
    "co-worker": "coworker",
    "babysitter": "babysitter",
    "cosplay": "cosplay",
    "parody": "parody",
    "fly on the wall": "fly on the wall",
    "third person": "third person view",
    "close up": "close up",
    "full body": "full body",
    "overhead": "overhead view",
    "low angle": "low angle",
    "side view": "side view",
    "behind camera": "from behind camera",
    "face cam": "face cam",
    "looking at camera": "looking at camera",
    "mirror": "mirror sex",
    "handheld": "handheld camera",
    "tripod": "tripod camera",
    "gopro": "gopro",
    "selfie cam": "selfie",
    "two camera": "two camera",
    "cinematic": "cinematic",
    "over the shoulder": "over the shoulder",
    "wide shot": "wide shot",
}

CANON_KEYS = {
    "step-sis": "step-sis",
    "stepsis": "step-sis",
    "step-sister": "step-sis",
    "stepsister": "step-sis",
    "only-fans": "onlyfans",
    "onlyfans": "onlyfans",
    "ai-generated": "ai",
    "ai": "ai",
    "home-made": "homemade",
    "homemade": "homemade",
    "18-teen": "teen",
    "18+-teen": "teen",
    "teen": "teen",
    "big-tits": "big tits",
    "tan-line": "tan line",
    "tanlines": "tan line",
    "small-tits": "small tits",
    "tiny-tits": "small tits",
    "tiny-boobs": "small tits",
    "small-boobs": "small tits",
    "little-tits": "small tits",
    "flat-chest": "small tits",
    "medium-tits": "medium tits",
    "medium-boobs": "medium tits",
    "large-tits": "large tits",
    "huge-tits": "large tits",
    "giant-tits": "large tits",
    "massive-tits": "large tits",
    "huge-boobs": "large tits",
    "big-boobs": "big tits",
    "busty": "large tits",
    "natural-tits": "natural tits",
    "perky-tits": "perky tits",
    "large-ass": "large ass",
    "big-ass": "large ass",
    "round-ass": "round ass",
    "lap-dance": "lap dance",
    "lapdance": "lap dance",
    "strip-tease": "striptease",
    "story-line": "storyline",
    "full-movie": "full movie",
    "full-scene": "full scene",
    "cuckold": "cuckold",
    "doggy": "doggy",
    "doggystyle": "doggy",
    "doggy-style": "doggy",
    "reverse-cowgirl": "reverse cowgirl",
    "reversecowgirl": "reverse cowgirl",
    "prone-bone": "prone bone",
    "pronebone": "prone bone",
    "mating-press": "mating press",
    "face-sitting": "facesitting",
    "facesitting": "facesitting",
    "legs-up": "legs up",
    "bent-over": "bent over",
    "full-nelson": "full nelson",
    "against-wall": "against wall",
    "against-the-wall": "against wall",
    "sixty-nine": "69",
    "redhead": "redhead",
    "red-hair": "redhead",
    "black-hair": "black hair",
    "pink-hair": "pink hair",
    "blue-hair": "blue hair",
    "purple-hair": "purple hair",
    "grey-hair": "grey",
    "gray": "grey",
    "cellphone": "cellphone",
    "phone-video": "cellphone",
    "snapchat": "snapchat",
    "hotel-sex": "hotel",
    "motel-sex": "motel",
    "car-sex": "car",
    "public-sex": "public",
    "sneaky-sex": "sneaky",
    "tramp-stamp": "tramp stamp",
    "delivery-guy": "delivery guy",
    "maintenance-man": "maintenance man",
    "co-worker": "co-worker",
    "coworker": "co-worker",
    "office-sex": "co-worker",
    "babysitter": "babysitter",
    "baby-sitter": "babysitter",
    "nanny": "babysitter",
    "cosplay": "cosplay",
    "costume-play": "cosplay",
    "parody": "parody",
    "porn-parody": "parody",
    "xxx-parody": "parody",
    "maintaince-man": "maintenance man",
    "fly-on-the-wall": "fly on the wall",
    "third-person": "third person",
    "close-up": "close up",
    "closeup": "close up",
    "full-body": "full body",
    "low-angle": "low angle",
    "side-view": "side view",
    "behind-camera": "behind camera",
    "from-behind-camera": "behind camera",
    "face-cam": "face cam",
    "looking-at-camera": "looking at camera",
    "selfie-cam": "selfie cam",
    "two-camera": "two camera",
    "over-the-shoulder": "over the shoulder",
    "wide-shot": "wide shot",
    "wide-angle": "wide shot",
    "socks": "socks",
    "sock": "socks",
    "sockjob": "socks",
    "michigan": "michigan",
    "michigan-position": "michigan",
    "slipped-in": "slipped in",
    "slipped-it-in": "slipped in",
    "accidentally-slipped-it-in": "slipped in",
    "accidentally-slipped-in": "slipped in",
}


def canon_query(query: str) -> str:
    raw = (query or "").strip().lower()
    dashed = re.sub(r"[\s_]+", "-", raw)
    spaced = re.sub(r"[\s_-]+", " ", raw).strip()
    return CANON_KEYS.get(dashed) or CANON_KEYS.get(spaced) or raw


def expand_search_query(query: str) -> str:
    if is_feed(query):
        return query
    key = canon_query(query)
    return SEARCH_PHRASE.get(key) or (query or "").strip()


def ranking_terms(query: str) -> list[str]:
    key = canon_query(query)
    phrases = list(CATEGORY_ALIASES.get(key, []))
    phrases.append((query or "").strip().lower())
    expanded = expand_search_query(query)
    if expanded and expanded.lower() not in phrases:
        phrases.append(expanded.lower())
    terms: list[str] = []
    for phrase in phrases:
        norm = re.sub(r"[^a-z0-9]+", " ", phrase).strip()
        if not norm:
            continue
        terms.append(norm)
        for token in norm.split():
            if token not in STOP_WORDS and (len(token) >= 2 or token == "ai"):
                terms.append(token)
        compact = re.sub(r"[^a-z0-9]+", "", phrase)
        if len(compact) >= 3:
            terms.append(compact)
    return list(dict.fromkeys(terms))


def relevance_score(item: dict, terms: list[str]) -> int:
    title = re.sub(r"[^a-z0-9]+", " ", html.unescape(str(item.get("title") or "")).lower()).strip()
    page = re.sub(r"[^a-z0-9]+", " ", str(item.get("page") or item.get("url") or "").lower()).strip()
    compact = title.replace(" ", "")
    if not terms:
        return 1
    score = 0
    for term in terms:
        if " " in term:
            if term in title:
                score += 12
            elif term in page:
                score += 4
            continue
        if term == "ai":
            if re.search(r"\bai\b", title):
                score += 10
            elif re.search(r"\bai\b", page):
                score += 3
            continue
        if re.search(rf"\b{re.escape(term)}\b", title):
            score += 6
        elif term in compact and len(term) >= 4:
            score += 5
        elif re.search(rf"\b{re.escape(term)}\b", page):
            score += 2
    return score


LENGTH_TAGS = {"short", "long"}
SHORT_MAX = 10 * 60
LONG_MIN = 20 * 60


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    tags = []
    for part in str(raw).split(","):
        tag = part.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break
    return tags


def split_length_tags(tags: list[str]) -> tuple[list[str], str]:
    length = next((tag for tag in tags if tag in LENGTH_TAGS), "")
    content = [tag for tag in tags if tag not in LENGTH_TAGS]
    return content, length


def duration_seconds(item: dict) -> int:
    text = clean_duration(str(item.get("duration") or ""))
    if not text:
        return 0
    parts = text.split(":")
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return 0
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return 0


def matches_length(item: dict, length: str) -> bool:
    if not length:
        return True
    secs = duration_seconds(item)
    if secs <= 0:
        return False
    if length == "short":
        return secs <= SHORT_MAX
    if length == "long":
        return secs >= LONG_MIN
    return True


def combine_search_query(tags: list[str]) -> str:
    words: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        for word in expand_search_query(tag).split():
            key = word.lower()
            if key in STOP_WORDS or key in seen:
                continue
            seen.add(key)
            words.append(word)
            if len(words) >= 5:
                return " ".join(words)
    return " ".join(words)


STYLE_OR_CAMERA = {
    "cellphone", "snapchat", "homemade", "amateur", "onlyfans", "ai", "pov",
    "fly on the wall", "third person", "close up", "full body", "overhead",
    "low angle", "side view", "behind camera", "face cam", "looking at camera",
    "mirror", "handheld", "tripod", "gopro", "selfie cam", "two camera",
    "cinematic", "over the shoulder", "wide shot",
}


def focused_search_query(tags: list[str]) -> str:
    def spec(tag: str) -> int:
        score = sum(len(tok) for tok in distinctive_tokens(tag))
        if " " in expand_search_query(tag):
            score += 4
        if canon_query(tag) in STYLE_OR_CAMERA:
            score -= 8
        return score

    ranked = sorted(tags, key=spec, reverse=True)
    phrases: list[str] = []
    seen: set[str] = set()
    for tag in ranked[:2]:
        phrase = expand_search_query(tag)
        key = phrase.lower()
        if phrase and key not in seen:
            seen.add(key)
            phrases.append(phrase)
    return " ".join(phrases) or combine_search_query(ranked[:3])


WEAK_SOLO = {
    "black", "dark", "red", "pink", "blue", "purple", "grey", "gray", "silver",
    "large", "small", "medium", "big", "huge", "tiny", "little", "round", "full",
    "close", "wide", "low", "side", "third", "two", "over", "looking", "from",
    "behind", "against", "natural", "perky", "fake",
    "tits", "tit", "boobs", "boob", "ass", "butt", "booty", "breasts", "breast",
}

PHRASE_ONLY = {
    "amazon", "butterfly", "black hair", "pink hair", "blue hair", "purple hair",
    "looking at camera", "over the shoulder", "fly on the wall", "third person",
    "behind camera", "delivery guy", "maintenance man", "tramp stamp", "tan line",
    "anvil", "lotus", "co-worker",
}

NEGATE = {
    "small tits": (
        "huge tits", "massive tits", "enormous tits", "giant tits",
        "big tits", "large tits", "huge boobs", "massive boobs", "big boobs",
    ),
    "large tits": ("small tits", "tiny tits", "flat chest", "little tits", "small boobs", "tiny boobs"),
    "big tits": ("small tits", "tiny tits", "flat chest", "little tits", "small boobs", "tiny boobs"),
    "medium tits": ("huge tits", "massive tits", "giant tits", "tiny tits", "flat chest"),
    "large ass": ("flat ass", "no ass", "skinny ass"),
    "round ass": ("flat ass",),
    "petite": ("bbw", "ssbbw", "plus size"),
    "natural tits": ("fake tits", "fake boobs", "implants", "fake breasts"),
    "blonde": ("brunette", "redhead", "ginger", "black hair", "brown hair"),
    "brunette": ("blonde", "blond", "redhead", "ginger", "platinum"),
    "redhead": ("blonde", "blond", "brunette", "black hair", "platinum"),
    "black hair": ("blonde", "blond", "redhead", "ginger", "platinum"),
    "platinum": ("brunette", "redhead", "ginger", "black hair", "brown hair"),
}


def tag_aliases(tag: str) -> list[str]:
    key = canon_query(tag)
    aliases = list(CATEGORY_ALIASES.get(key, []))
    if key not in PHRASE_ONLY:
        aliases.append(key)
    expanded = expand_search_query(tag)
    if expanded and expanded.lower() not in {a.lower() for a in aliases}:
        aliases.append(expanded)
    return list(dict.fromkeys(aliases))


def tokens_near(title: str, toks: list[str], window: int = 28) -> bool:
    if len(toks) <= 1:
        return True
    starts: list[int] = []
    for tok in toks:
        match = re.search(rf"\b{re.escape(tok)}\b", title)
        if not match:
            return True
        starts.append(match.start())
    return max(starts) - min(starts) <= window + sum(len(tok) for tok in toks)


def alias_hits_title(title: str, compact: str, alias: str) -> bool:
    phrase = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
    if not phrase:
        return False
    if " " not in phrase:
        if re.search(rf"\b{re.escape(phrase)}\b", title):
            return True
    elif phrase in title:
        return True
    glued = phrase.replace(" ", "")
    if len(glued) >= 5 and glued in compact:
        return True
    words = [tok for tok in phrase.split() if tok]
    toks = [tok for tok in words if tok not in STOP_WORDS and (len(tok) >= 2 or tok == "ai")]
    if not toks:
        return False
    if len(words) > 1 and len(toks) == 1:
        return False
    if all(tok in WEAK_SOLO or len(tok) < 4 for tok in toks):
        return False
    if not all(token_in_item(tok, title, "", compact) for tok in toks):
        return False
    return tokens_near(title, toks)


def distinctive_tokens(query: str) -> list[str]:
    key = canon_query(query)
    tokens: list[str] = []
    for token in re.sub(r"[^a-z0-9]+", " ", key.lower()).split():
        if token in STOP_WORDS:
            continue
        if len(token) >= 2 or token == "ai":
            tokens.append(token)
    if tokens:
        return list(dict.fromkeys(tokens))
    phrase = expand_search_query(query)
    for token in re.sub(r"[^a-z0-9]+", " ", phrase.lower()).split():
        if token in STOP_WORDS:
            continue
        if len(token) >= 2 or token == "ai":
            tokens.append(token)
    return list(dict.fromkeys(tokens))


def item_text(item: dict) -> tuple[str, str, str]:
    title = re.sub(r"[^a-z0-9]+", " ", html.unescape(str(item.get("title") or "")).lower()).strip()
    page = re.sub(r"[^a-z0-9]+", " ", str(item.get("page") or item.get("url") or "").lower()).strip()
    return title, page, title.replace(" ", "")


def token_in_item(token: str, title: str, page: str, compact: str) -> bool:
    if token == "ai":
        return bool(re.search(r"\bai\b", title) or re.search(r"\bai\b", page))
    if re.search(rf"\b{re.escape(token)}\b", title):
        return True
    if len(token) >= 4 and token in compact:
        return True
    return bool(re.search(rf"\b{re.escape(token)}\b", page))


def tag_matched(item: dict, tag: str) -> bool:
    title, _page, compact = item_text(item)
    key = canon_query(tag)
    aliases = tag_aliases(tag)
    if any(neg in title for neg in NEGATE.get(key, ())):
        if not any(alias_hits_title(title, compact, alias) for alias in aliases):
            return False
    if any(alias_hits_title(title, compact, alias) for alias in aliases):
        return True
    if key in PHRASE_ONLY:
        return False
    tokens = distinctive_tokens(tag)
    strong = [tok for tok in tokens if tok not in WEAK_SOLO and len(tok) >= 4]
    if not strong:
        return False
    if tokens and all(token_in_item(token, title, "", compact) for token in tokens):
        return tokens_near(title, tokens)
    return False


def tag_strength(item: dict, tag: str) -> int:
    title, _page, compact = item_text(item)
    if not tag_matched(item, tag):
        return 0
    for alias in tag_aliases(tag):
        phrase = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
        if phrase and phrase in title:
            return 3
        glued = phrase.replace(" ", "")
        if phrase and len(glued) >= 5 and glued in compact:
            return 3
    return 2


def query_as_tags(query: str) -> list[str]:
    key = canon_query(query)
    if key in CATEGORY_ALIASES:
        return [key]
    blob = re.sub(r"[^a-z0-9]+", " ", (query or "").lower()).strip()
    if not blob:
        return []
    found: list[str] = []
    for name in sorted(CATEGORY_ALIASES, key=len, reverse=True):
        for alias in tag_aliases(name):
            phrase = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
            if phrase and re.search(rf"\b{re.escape(phrase)}\b", blob):
                if name not in found:
                    found.append(name)
                break
        if len(found) >= 4:
            break
    return found


def rank_items(items: list[dict], query: str, tags: list[str] | None = None) -> list[dict]:
    tag_list = [tag for tag in (tags or []) if tag]
    if not tag_list:
        tag_list = query_as_tags(query)
    if tag_list:
        terms = list(dict.fromkeys(term for tag in tag_list for term in ranking_terms(tag)))
        scored = []
        for item in items:
            hits = sum(1 for tag in tag_list if tag_matched(item, tag))
            strength = sum(tag_strength(item, tag) for tag in tag_list)
            score = relevance_score(item, terms) + strength * 3
            scored.append((hits, strength, score, item))
        scored.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
        total = len(tag_list)
        full = [item for hits, _st, _score, item in scored if hits >= total]
        if total >= 2:
            return full
        almost = [item for hits, _st, _score, item in scored if hits >= max(1, total - 1)]
        some = [item for hits, _st, _score, item in scored if hits > 0]
        if full:
            return full
        if almost:
            return almost
        return some
    tokens = distinctive_tokens(query)
    terms = ranking_terms(query)
    scored = []
    for item in items:
        title, _page, compact = item_text(item)
        title_hits = sum(1 for token in tokens if token_in_item(token, title, "", compact)) if tokens else 0
        score = relevance_score(item, terms) + title_hits * 4
        scored.append((title_hits, score, item))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    if not tokens:
        return [item for _t, _s, item in scored]
    needed = len(tokens) if len(tokens) <= 3 else max(2, (len(tokens) * 2 + 2) // 3)
    strong = [item for title_hits, _score, item in scored if title_hits >= needed]
    if strong:
        return strong
    if needed > 1:
        softer = [item for title_hits, _score, item in scored if title_hits >= needed - 1]
        if softer:
            return softer
    return [item for title_hits, _score, item in scored if title_hits > 0]


def interleave_by_source(items: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    order: list[str] = []
    for row in items:
        src = str(row.get("source") or "")
        if src not in buckets:
            buckets[src] = []
            order.append(src)
        buckets[src].append(row)
    out: list[dict] = []
    while any(buckets[name] for name in order):
        for name in order:
            if buckets[name]:
                out.append(buckets[name].pop(0))
    return out


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
        sock.close()
        return address
    except OSError:
        return "127.0.0.1"


def fetch(url: str, headers: dict | None = None, timeout: int = 12) -> bytes:
    request = Request(url, headers={"User-Agent": BROWSER_UA, **(headers or {})})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except URLError as error:
        if "certificate" not in str(error).lower() and "SSL" not in str(error):
            raise
        with urlopen(request, timeout=timeout, context=SSL_LOOSE) as response:
            return response.read()


def blocked_query(query: str) -> str | None:
    if BLOCK.search(query or ""):
        return BLOCK_REASON
    return None


def host_blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return any(bit in host for bit in BLOCKED_HOST_BITS)


def clean_duration(raw: str) -> str:
    text = html.unescape(str(raw or "")).strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d{1,5}", text):
        total = int(text)
        if total <= 0 or total > 12 * 3600:
            return ""
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
    match = re.search(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})", text)
    if match:
        hour, minute, second = match.group(1), int(match.group(2)), int(match.group(3))
        if second > 59:
            return ""
        if hour:
            return f"{int(hour)}:{minute:02d}:{second:02d}"
        return f"{minute}:{second:02d}"
    match = re.search(r"(\d{1,3})\s*(?:min|mins|minutes)\b", text, re.I)
    if match:
        return f"{int(match.group(1))}:00"
    return ""


def pick_duration(chunk: str) -> str:
    if not chunk:
        return ""
    for raw in re.findall(
        r'(?:class|id)="[^"]*(?:duration|runtime|video-time|video-duration|length)[^"]*"[^>]*>([^<]{1,32})',
        chunk,
        re.I,
    ):
        got = clean_duration(raw)
        if got:
            return got
    times = [clean_duration(item) for item in re.findall(r"(?<!\d)(\d{1,2}:\d{2}(?::\d{2})?)(?!\d)", chunk)]
    times = [item for item in times if item]
    if times:
        return times[-1]
    mins = re.search(r"(\d{1,3})\s*(?:min|mins|minutes)\b", chunk, re.I)
    return clean_duration(mins.group(0)) if mins else ""


def attach_durations(items: list[dict], body: str) -> list[dict]:
    for item in items:
        current = clean_duration(item.get("duration") or "")
        if current:
            item["duration"] = current
            continue
        needle = item.get("thumb") or item.get("page") or ""
        idx = body.find(needle[:90]) if needle else -1
        if idx < 0 and item.get("page"):
            idx = body.find(item["page"][-60:])
        if idx < 0:
            continue
        item["duration"] = pick_duration(body[max(0, idx - 400) : idx + 2800])
    return items


def video_item(provider: str, source: str, title: str, page: str, thumb: str, embed: str, duration: str) -> dict:
    key = hashlib.sha1((page or thumb or title).encode("utf-8", "ignore")).hexdigest()[:16]
    return {
        "id": f"{source}-{key}",
        "provider": provider,
        "source": source,
        "title": html.unescape(title or "")[:180],
        "page": page,
        "url": page,
        "thumb": clean_thumb(thumb),
        "embed": embed,
        "duration": clean_duration(duration),
    }


def allowed_item(row: dict) -> bool:
    blob = " ".join(str(row.get(key) or "") for key in ("title", "page", "url", "provider"))
    if blocked_query(blob):
        return False
    return not any(host_blocked(row.get(key) or "") for key in ("page", "url", "thumb", "embed"))


def pornhub_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    if kind == "new":
        params = urlencode({"thumbsize": "large", "ordering": "newest", "page": page + 1})
    elif kind == "views":
        params = urlencode({"thumbsize": "large", "ordering": "mostviewed", "page": page + 1})
    else:
        params = urlencode({"search": query, "thumbsize": "large", "page": page + 1})
    data = json.loads(fetch(f"https://www.pornhub.com/webmasters/search?{params}", {"Accept": "application/json"}))
    items = []
    for row in data.get("videos") or []:
        page_url = row.get("url") or ""
        viewkey = ""
        if "viewkey=" in page_url:
            viewkey = page_url.split("viewkey=", 1)[1].split("&", 1)[0]
        embed = f"https://www.pornhub.com/embed/{viewkey}" if viewkey else ""
        items.append(
            video_item(
                "Pornhub",
                "pornhub",
                row.get("title") or "",
                page_url,
                row.get("default_thumb") or row.get("thumb") or "",
                embed,
                row.get("duration") or "",
            )
        )
    return items


def youporn_search(query: str, page: int) -> list[dict]:
    params = urlencode({"search": query, "thumbsize": "large", "page": page + 1})
    data = json.loads(fetch(f"https://www.youporn.com/api/webmasters/search?{params}", {"Accept": "application/json"}))
    items = []
    for row in data.get("video") or data.get("videos") or []:
        page_url = row.get("url") or ""
        embed = row.get("embed") or ""
        if not embed and "/watch/" in page_url:
            slug = page_url.rstrip("/").split("/")[-1]
            embed = f"https://www.youporn.com/embed/{slug}"
        items.append(
            video_item(
                "YouPorn",
                "youporn",
                row.get("title") or "",
                page_url,
                row.get("default_thumb") or row.get("thumb") or "",
                embed,
                str(row.get("duration") or ""),
            )
        )
    return items


def redtube_search(query: str, page: int) -> list[dict]:
    params = {
        "data": "redtube.Videos.searchVideos",
        "output": "json",
        "thumbsize": "medium",
        "page": page + 1,
    }
    kind = feed_kind(query)
    if kind == "new":
        params["ordering"] = "newest"
    elif kind == "views":
        params["ordering"] = "mostviewed"
    else:
        params["search"] = query
    params = urlencode(params)
    data = json.loads(fetch(f"https://api.redtube.com/?{params}", {"Accept": "application/json"}))
    items = []
    for wrap in data.get("videos") or []:
        row = wrap.get("video") or wrap
        video_id = str(row.get("video_id") or "")
        embed = f"https://embed.redtube.com/?id={video_id}" if video_id else ""
        items.append(
            video_item(
                "RedTube",
                "redtube",
                row.get("title") or "",
                row.get("url") or "",
                row.get("default_thumb") or row.get("thumb") or "",
                embed,
                str(row.get("duration") or ""),
            )
        )
    return items


def eporner_search(query: str, page: int) -> list[dict]:
    params = urlencode(
        {
            "query": "" if feed_kind(query) else query,
            "per_page": 20,
            "page": page + 1,
            "thumbsize": "medium",
            "order": "most-popular" if feed_kind(query) == "views" else "latest",
            "gay": 0,
            "lq": 1,
            "format": "json",
        }
    )
    data = json.loads(fetch(f"https://www.eporner.com/api/v2/video/search/?{params}", {"Accept": "application/json"}))
    items = []
    for row in data.get("videos") or []:
        thumb = ""
        default_thumb = row.get("default_thumb")
        if isinstance(default_thumb, dict):
            thumb = default_thumb.get("src") or ""
        elif isinstance(default_thumb, str):
            thumb = default_thumb
        embed = row.get("embed") or ""
        if not embed and row.get("id"):
            embed = f"https://www.eporner.com/embed/{row.get('id')}"
        items.append(
            video_item(
                "Eporner",
                "eporner",
                row.get("title") or "",
                row.get("url") or "",
                thumb,
                embed,
                str(row.get("length_min") or row.get("length_sec") or ""),
            )
        )
    return items


def clean_thumb(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    low = url.lower()
    if any(bad in low for bad in ("blank.gif", "lightbox-blank", "placeholder", "pixel.gif", "1x1")):
        return ""
    # rdtcdn currently serves an expired certificate; MindGeek thumbs still work on phncdn.
    url = url.replace("ei-ph.rdtcdn.com", "ei.phncdn.com").replace(".rdtcdn.com", ".phncdn.com")
    return url


def xvideos_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    if kind == "new":
        target = "https://www.xvideos.com/" if page == 0 else f"https://www.xvideos.com/new/{page + 1}"
    elif kind == "views":
        target = "https://www.xvideos.com/best/" if page == 0 else f"https://www.xvideos.com/best/{page + 1}"
    else:
        target = f"https://www.xvideos.com/?k={quote(query)}&p={page}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.xvideos.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(/video[^"]+)"[\s\S]{0,900}?data-src="(https://[^"]+)"',
        body,
        re.I,
    ):
        path, thumb = match.group(1), clean_thumb(match.group(2))
        if not thumb or not path.startswith("/video"):
            continue
        page_url = "https://www.xvideos.com" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        title = path.rstrip("/").split("/")[-1].replace("_", " ")
        dur = ""
        dur_m = re.search(r'class="duration"[^>]*>([^<]+)', match.group(0), re.I)
        if dur_m:
            dur = dur_m.group(1).strip()
        items.append(video_item("XVideos", "xvideos", title, page_url, thumb, "", dur))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def xnxx_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    if kind == "new":
        target = "https://www.xnxx.com/" if page == 0 else f"https://www.xnxx.com/new/{page + 1}"
    elif kind == "views":
        target = "https://www.xnxx.com/best/" if page == 0 else f"https://www.xnxx.com/best/{page + 1}"
    else:
        path_page = "" if page == 0 else f"/{page}"
        target = f"https://www.xnxx.com/search/{quote(query)}{path_page}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.xnxx.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(/video-[^"]+)"[\s\S]{0,900}?data-src="(https://[^"]+)"',
        body,
        re.I,
    ):
        path, thumb = match.group(1), clean_thumb(match.group(2))
        if not thumb:
            continue
        page_url = "https://www.xnxx.com" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        title = path.rstrip("/").split("/")[-1].replace("_", " ").replace("-", " ")
        items.append(video_item("XNXX", "xnxx", title, page_url, thumb, "", ""))
        if len(items) >= 48:
            break
    return attach_durations(items, body)


def xhamster_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    if kind == "new":
        suffix = "" if page == 0 else f"/{page + 1}"
        target = f"https://xhamster.com/newest{suffix}"
    elif kind == "views":
        suffix = "" if page == 0 else f"/{page + 1}"
        target = f"https://xhamster.com/best{suffix}"
    else:
        suffix = "" if page == 0 else f"?page={page + 1}"
        target = f"https://xhamster.com/search/{quote(query)}{suffix}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://xhamster.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(https://xhamster\.com/videos/[^"]+)"[^>]*>.*?(?:src|data-src)="(https://[^"]+)"',
        body,
        re.I | re.S,
    ):
        page_url, thumb = match.group(1), match.group(2)
        page_url = page_url.split("?")[0]
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("xHamster", "xhamster", title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def hqporner_search(query: str, page: int) -> list[dict]:
    extra = f"&p={page + 1}" if page else ""
    target = f"https://hqporner.com/?q={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://hqporner.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(/hdporn/[^"]+)"[\s\S]{0,900}?defaultImage\("(//[^"]+)"',
        body,
        re.I,
    ):
        path, thumb = match.group(1), clean_thumb(match.group(2))
        page_url = "https://hqporner.com" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        title = re.sub(r"^\d+-", "", path.rsplit("/", 1)[-1].replace(".html", "")).replace("_", " ")
        items.append(video_item("HQPorner", "hqporner", title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    if not items:
        hrefs = re.findall(r'href="(/hdporn/[^"]+)"', body)
        thumbs = [clean_thumb("https:" + u) if u.startswith("//") else clean_thumb(u)
                  for u in re.findall(r'(//fastporndelivery\.hqporner\.com/imgs/[^"\']+_main\.jpg)', body)]
        for path, thumb in zip(dict.fromkeys(hrefs), thumbs):
            page_url = "https://hqporner.com" + path
            title = re.sub(r"^\d+-", "", path.rsplit("/", 1)[-1].replace(".html", "")).replace("_", " ")
            items.append(video_item("HQPorner", "hqporner", title, page_url, thumb, "", ""))
    return attach_durations(items, body)


def xxxbunker_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    extra = f"/{page + 1}" if page else ""
    if kind == "new":
        target = f"https://xxxbunker.com/{extra.lstrip('/')}" if extra else "https://xxxbunker.com/"
    elif kind == "views":
        target = f"https://xxxbunker.com/top{extra}"
    else:
        q = quote(query).replace("%20", "+")
        extra = f"/{page + 1}" if page else ""
        target = f"https://xxxbunker.com/search/{q}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://xxxbunker.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for vid, title in re.findall(
        r'(?:src|data-src)="https://thumbs\.xxxbunker\.com/(\d+)\.jpg"[^>]*alt="([^"]*)"',
        body,
        re.I,
    ):
        page_url = f"https://xxxbunker.com/{vid}"
        if page_url in seen:
            continue
        seen.add(page_url)
        items.append(
            video_item("XXXBunker", "xxxbunker", title or vid, page_url, f"https://thumbs.xxxbunker.com/{vid}.jpg", "", "")
        )
        if len(items) >= 40:
            break
    if not items:
        for vid in re.findall(r"https://thumbs\.xxxbunker\.com/(\d+)\.jpg", body):
            page_url = f"https://xxxbunker.com/{vid}"
            if page_url in seen:
                continue
            seen.add(page_url)
            items.append(
                video_item("XXXBunker", "xxxbunker", vid, page_url, f"https://thumbs.xxxbunker.com/{vid}.jpg", "", "")
            )
            if len(items) >= 40:
                break
    return attach_durations(items, body)


def tnaflix_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    if kind == "new":
        extra = f"?page={page + 1}" if page else ""
        target = f"https://www.tnaflix.com/{extra}"
    elif kind == "views":
        extra = f"?page={page + 1}" if page else ""
        target = f"https://www.tnaflix.com/popular{extra}"
    else:
        extra = f"&page={page + 1}" if page else ""
        target = f"https://www.tnaflix.com/search.php?what={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.tnaflix.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for chunk in re.findall(r'(<div data-vid="\d+"[\s\S]{0,3000}?</div>\s*</div>)', body, re.I):
        vid_m = re.search(r'data-vid="(\d+)"', chunk)
        href_m = re.search(r'href="(https://www\.tnaflix\.com/[^"]+/video\d+)"', chunk)
        thumb_m = re.search(r'(?:data-src|src)="(https://(?:cdnl|img)\.tnaflix\.com/[^"]+\.jpg)"', chunk)
        if not vid_m or not href_m:
            continue
        page_url = href_m.group(1)
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.split("/video")[0].rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("TNAflix", "tnaflix", title, page_url, clean_thumb(thumb_m.group(1) if thumb_m else ""), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def drtuber_search(query: str, page: int) -> list[dict]:
    extra = f"/{page + 1}" if page else ""
    kind = feed_kind(query)
    if kind == "new":
        target = "https://www.drtuber.com/latest-updates/" if page == 0 else f"https://www.drtuber.com/latest-updates/{page + 1}"
    elif kind == "views":
        target = "https://www.drtuber.com/most-popular/" if page == 0 else f"https://www.drtuber.com/most-popular/{page + 1}"
    else:
        target = f"https://www.drtuber.com/search/videos/{quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.drtuber.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for path, thumb in re.findall(
        r'href="(/video/\d+/[^"]+)"[^>]*>\s*<img[^>]+src="(https://[^"]+)"',
        body,
        re.I,
    ):
        page_url = "https://www.drtuber.com" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        title = path.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("DrTuber", "drtuber", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def sunporno_search(query: str, page: int) -> list[dict]:
    extra = f"{page + 1}/" if page else ""
    target = f"https://www.sunporno.com/search/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.sunporno.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for page_url, thumb in re.findall(
        r'href="(https://www\.sunporno\.com/v/\d+/[^"]+)"[\s\S]{0,500}?src="(https://acdn\.sunporno\.com/[^"]+)"',
        body,
        re.I,
    ):
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("SunPorno", "sunporno", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    if not items:
        for thumb, page_url in re.findall(
            r'src="(https://acdn\.sunporno\.com/contents/videos_screenshots/[^"]+)"[\s\S]{0,400}?href="(https://www\.sunporno\.com/v/\d+/[^"]+)"',
            body,
            re.I,
        ):
            if page_url in seen:
                continue
            seen.add(page_url)
            title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
            items.append(video_item("SunPorno", "sunporno", title, page_url, clean_thumb(thumb), "", ""))
            if len(items) >= 40:
                break
    return attach_durations(items, body)


def pornone_search(query: str, page: int) -> list[dict]:
    extra = f"/{page + 1}" if page else ""
    kind = feed_kind(query)
    if kind == "new":
        target = "https://www.pornone.com/" if page == 0 else f"https://www.pornone.com/{page + 1}/"
    elif kind == "views":
        target = "https://www.pornone.com/most-viewed/" if page == 0 else f"https://www.pornone.com/most-viewed/{page + 1}/"
    else:
        target = f"https://www.pornone.com/search{extra}/?q={quote(query)}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.pornone.com/"}).decode("utf-8", "ignore")
    thumbs = {}
    for thumb in re.findall(r'(https://th-eu\d+\.pornone\.com/t/\d+/(\d+)/[^"\s]+)', body):
        thumbs[thumb[1]] = clean_thumb(thumb[0])
    items = []
    seen = set()
    for page_url, vid in re.findall(r'href="(https://(?:www\.)?pornone\.com/[^"]+/(\d+)/)"', body, re.I):
        page_url = page_url.replace("http://", "https://")
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-2].replace("-", " ")
        items.append(video_item("PornOne", "pornone", title, page_url, thumbs.get(vid, ""), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def tube8_search(query: str, page: int) -> list[dict]:
    extra = f"&page={page + 1}" if page else ""
    target = f"https://www.tube8.com/searches.html?q={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.tube8.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(https://www\.tube8\.com/[a-z0-9-]+/[a-z0-9-]+/\d+/)"[\s\S]{0,700}?(?:data-src|src)="(https://[^"]+\.(?:jpg|jpeg|webp))"',
        body,
        re.I,
    ):
        page_url, thumb = match.group(1), clean_thumb(match.group(2))
        if page_url in seen or "cat_" in thumb:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-2].replace("-", " ")
        items.append(video_item("Tube8", "tube8", title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def okxxx_search(query: str, page: int) -> list[dict]:
    extra = f"?from_videos={page + 1}" if page else ""
    kind = feed_kind(query)
    if kind == "new":
        target = "https://ok.xxx/latest-updates/" if page == 0 else f"https://ok.xxx/latest-updates/{page + 1}/"
    elif kind == "views":
        target = "https://ok.xxx/most-popular/" if page == 0 else f"https://ok.xxx/most-popular/{page + 1}/"
    else:
        target = f"https://ok.xxx/search/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://ok.xxx/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for path, title, thumb in re.findall(
        r'href="(/video/\d+/)"[^>]*title="([^"]*)"[\s\S]{0,700}?data-original="(https://[^"]+)"',
        body,
        re.I,
    ):
        page_url = "https://ok.xxx" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        items.append(video_item("OK.xxx", "okxxx", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def porn00_search(query: str, page: int) -> list[dict]:
    extra = f"{page + 1}/" if page else ""
    kind = feed_kind(query)
    if kind == "new":
        target = "https://www.porn00.org/latest/" if page == 0 else f"https://www.porn00.org/latest/{page + 1}/"
    elif kind == "views":
        target = "https://www.porn00.org/most-popular/" if page == 0 else f"https://www.porn00.org/most-popular/{page + 1}/"
    else:
        target = f"https://www.porn00.org/q/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.porn00.org/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for page_url, title, thumb in re.findall(
        r'href="(https://www.porn00.org/video/[^"]+)"[^>]*title="([^"]*)"[\s\S]{0,600}?data-original="(https://[^"]+)"',
        body,
        re.I,
    ):
        if page_url in seen:
            continue
        seen.add(page_url)
        items.append(video_item("Porn00", "porn00", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def xxxfiles_search(query: str, page: int) -> list[dict]:
    extra = f"&page={page + 1}" if page else ""
    kind = feed_kind(query)
    if kind:
        target = "https://www.xxxfiles.com/" if page == 0 else f"https://www.xxxfiles.com/page/{page + 1}/"
    else:
        target = f"https://www.xxxfiles.com/?s={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.xxxfiles.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for page_url, thumb in re.findall(
        r'href="(https://www.xxxfiles.com/videos/\d+/[^"]+)"[\s\S]{0,500}?src="(https://img.xxxfiles.com/[^"]+)"',
        body,
        re.I,
    ):
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-1]
        alt = re.search(r'alt="([^"]+)"', body[body.find(thumb): body.find(thumb) + 200] if thumb in body else "")
        if alt:
            title = alt.group(1)
        items.append(video_item("XXXFiles", "xxxfiles", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def xmoviesforyou_search(query: str, page: int) -> list[dict]:
    extra = f"&paged={page + 1}" if page else ""
    kind = feed_kind(query)
    if kind:
        target = "https://xmoviesforyou.com/" if page == 0 else f"https://xmoviesforyou.com/page/{page + 1}/"
    else:
        target = f"https://xmoviesforyou.com/?s={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://xmoviesforyou.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for path, thumb in re.findall(
        r'href="(/[a-z0-9-]+)"[^>]*>[\s\S]{0,500}?src="(https://xmoviescdn\.online/[^"]+)"',
        body,
        re.I,
    ):
        if path in ("/categories", "/tags", "/pornstars", "/studios"):
            continue
        page_url = "https://xmoviesforyou.com" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        title = path.strip("/").replace("-", " ")
        items.append(video_item("XMoviesForYou", "xmoviesforyou", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def whoreshub_search(query: str, page: int) -> list[dict]:
    extra = f"?from_videos={page + 1}" if page else ""
    kind = feed_kind(query)
    if kind == "new":
        target = "https://www.whoreshub.com/latest-updates/" if page == 0 else f"https://www.whoreshub.com/latest-updates/{page + 1}/"
    elif kind == "views":
        target = "https://www.whoreshub.com/most-popular/" if page == 0 else f"https://www.whoreshub.com/most-popular/{page + 1}/"
    else:
        target = f"https://www.whoreshub.com/search/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.whoreshub.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for page_url in re.findall(r'href="(https://www.whoreshub.com/videos/\d+/[^"]+)"', body, re.I):
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
        vid = re.search(r"/videos/(\d+)/", page_url)
        thumb = ""
        if vid:
            num = int(vid.group(1))
            bucket = (num // 1000) * 1000
            thumb = f"https://www.whoreshub.com/contents/videos_screenshots/{bucket}/{num}/320x180/1.jpg"
        items.append(video_item("WhoresHub", "whoreshub", title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def yespornvip_search(query: str, page: int) -> list[dict]:
    extra = f"&paged={page + 1}" if page else ""
    kind = feed_kind(query)
    if kind:
        target = "https://yespornvip.com/" if page == 0 else f"https://yespornvip.com/page/{page + 1}/"
    else:
        target = f"https://yespornvip.com/?s={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://yespornvip.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for page_url, thumb in re.findall(
        r'href="(https://yespornvip.com/[a-z0-9-]+/)"[\s\S]{0,800}?(?:data-src|src)="(https://yespornvip.com/wp-content/uploads/thumbsx/[^"]+)"',
        body,
        re.I,
    ):
        if any(part in page_url for part in ("/category/", "/search/", "/feed/", "/wp-json/")):
            continue
        if page_url in seen:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("YesPornVIP", "yespornvip", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    if not items:
        thumbs = re.findall(r'(?:data-src|src)="(https://yespornvip.com/wp-content/uploads/thumbsx/[^"]+)"', body, re.I)
        hrefs = [
            h for h in re.findall(r'href="(https://yespornvip.com/[a-z0-9-]+/)"', body, re.I)
            if not any(p in h for p in ("/category/", "/search/", "/feed/", "/wp-json/"))
        ]
        for page_url, thumb in zip(dict.fromkeys(hrefs), thumbs):
            title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
            items.append(video_item("YesPornVIP", "yespornvip", title, page_url, clean_thumb(thumb), "", ""))
            if len(items) >= 40:
                break
    return attach_durations(items, body)


def justporn_search(query: str, page: int) -> list[dict]:
    extra = f"page/{page + 1}/" if page else ""
    kind = feed_kind(query)
    if kind:
        target = "https://www.justporn.to/" if page == 0 else f"https://www.justporn.to/page/{page + 1}/"
    else:
        target = f"https://www.justporn.to/search/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.justporn.to/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for page_url, thumb in re.findall(
        r'href="(https://(?:www\.)?justporn.to/[a-z0-9-]+/)"[\s\S]{0,700}?src="(https://justporn.to/cover_upload/[^"]+)"',
        body,
        re.I,
    ):
        if page_url in seen or "/search/" in page_url:
            continue
        seen.add(page_url)
        title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("JustPorn", "justporn", title, page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def porndig_search(query: str, page: int) -> list[dict]:
    extra = f"&page={page + 1}" if page else ""
    target = f"https://www.porndig.com/{quote(query)}?q={quote(query)}{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.porndig.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for vid, thumb in re.findall(
        r'data-video_id="(\d+)"[\s\S]{0,200}?(?:data-src|src)="(https://image-cdn.porndig.com/[^"]+)"',
        body,
        re.I,
    ):
        page_url = f"https://www.porndig.com/videos/{vid}"
        if page_url in seen:
            continue
        seen.add(page_url)
        items.append(video_item("PornDig", "porndig", f"Video {vid}", page_url, clean_thumb(thumb), "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def homemadegalore_search(query: str, page: int) -> list[dict]:
    extra = f"?page={page + 1}" if page else ""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.homemadegalore.com/",
        "User-Agent": BROWSER_UA,
    }
    body = b""
    for target in (
        f"https://www.homemadegalore.com/search/{quote(query)}{extra}",
        f"https://homemadegalore.com/search/{quote(query)}{extra}",
        f"https://www.homemadegalore.com/search/{quote(query)}/{extra}",
    ):
        try:
            body = fetch(target, headers)
            if body:
                break
        except Exception:
            continue
    if not body:
        return []
    body = body.decode("utf-8", "ignore")
    items = []
    seen = set()
    for href, title, thumb in re.findall(
        r'href="(/out/\?l=[^"]+)"[^>]*title="([^"]+)"[^>]*>\s*<img[^>]+src="(https://c\d+\.ttcache\.com/[^"]+)"',
        body,
        re.I,
    ):
        page_url = "https://www.homemadegalore.com" + html.unescape(href)
        if page_url in seen:
            continue
        seen.add(page_url)
        items.append(
            video_item("HomemadeGalore", "homemadegalore", title, page_url, clean_thumb(thumb), "", "")
        )
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def kvs_search(provider: str, source: str, host: str, query: str, page: int) -> list[dict]:
    extra = f"?from_videos={page + 1}" if page else ""
    kind = feed_kind(query)
    if kind == "new":
        target = f"https://{host}/latest-updates/" if page == 0 else f"https://{host}/latest-updates/{page + 1}/"
    elif kind == "views":
        target = f"https://{host}/most-popular/" if page == 0 else f"https://{host}/most-popular/{page + 1}/"
    else:
        target = f"https://{host}/search/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": f"https://{host}/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    host_re = re.escape(host)
    for match in re.finditer(
        rf'href="((?:https://(?:www\.)?{host_re})?/(?:videos|video|movies)/(\d+)/[^"]+)"',
        body,
        re.I,
    ):
        path, vid = match.group(1), match.group(2)
        page_url = path if path.startswith("http") else f"https://{host}{path}"
        page_url = page_url.split("?")[0]
        if page_url in seen:
            continue
        seen.add(page_url)
        chunk = body[max(0, match.start() - 120) : match.end() + 900]
        thumb_m = re.search(
            r'(?:data-original|data-src|src)="((?:https:)?//[^"]+\.(?:jpg|jpeg|webp)[^"]*)"',
            chunk,
            re.I,
        )
        thumb = clean_thumb(thumb_m.group(1)) if thumb_m else ""
        if not thumb:
            num = int(vid)
            bucket = (num // 1000) * 1000
            thumb = f"https://{host}/contents/videos_screenshots/{bucket}/{num}/320x180/1.jpg"
        title = page_url.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item(provider, source, title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def txxx_search(query: str, page: int) -> list[dict]:
    return kvs_search("TXXX", "txxx", "txxx.com", query, page)


def threemovs_search(query: str, page: int) -> list[dict]:
    return kvs_search("3Movs", "3movs", "www.3movs.com", query, page)


def hdzog_search(query: str, page: int) -> list[dict]:
    return kvs_search("HDZog", "hdzog", "hdzog.com", query, page)


def hotmovs_search(query: str, page: int) -> list[dict]:
    return kvs_search("HotMovs", "hotmovs", "hotmovs.com", query, page)


def porngo_search(query: str, page: int) -> list[dict]:
    return kvs_search("PornGo", "porngo", "www.porngo.com", query, page)


def xozilla_search(query: str, page: int) -> list[dict]:
    return kvs_search("Xozilla", "xozilla", "www.xozilla.com", query, page)


def spankbang_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    extra = f"{page + 1}/" if page else ""
    if kind == "new":
        target = f"https://spankbang.com/new_videos/{extra}"
    elif kind == "views":
        target = f"https://spankbang.com/trending_videos/{extra}"
    else:
        extra = f"{page + 1}/" if page else ""
        target = f"https://spankbang.com/s/{quote(query)}/{extra}"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://spankbang.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(/[a-z0-9]+/video/[^"]+)"[\s\S]{0,900}?(?:data-src|src)="((?:https:)?//[^"]+\.(?:jpg|jpeg|webp)[^"]*)"',
        body,
        re.I,
    ):
        path, thumb = match.group(1), clean_thumb(match.group(2))
        if "/playlist/" in path or not thumb:
            continue
        page_url = "https://spankbang.com" + path.split("?")[0]
        if page_url in seen:
            continue
        seen.add(page_url)
        title = path.rstrip("/").split("/")[-1].replace("-", " ")
        items.append(video_item("SpankBang", "spankbang", title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


def youjizz_search(query: str, page: int) -> list[dict]:
    kind = feed_kind(query)
    if kind == "new":
        target = f"https://www.youjizz.com/newest-clips/{page + 1}.html"
    elif kind == "views":
        target = f"https://www.youjizz.com/most-popular/{page + 1}.html"
    else:
        slug = quote(query).replace("%20", "-")
        target = f"https://www.youjizz.com/search/{slug}-{page + 1}.html"
    body = fetch(target, {"Accept": "text/html", "Referer": "https://www.youjizz.com/"}).decode("utf-8", "ignore")
    items = []
    seen = set()
    for match in re.finditer(
        r'href="(/videos/[^"]+\.html)"[\s\S]{0,800}?(?:data-original|src)="((?:https:)?//[^"]+\.(?:jpg|jpeg|webp)[^"]*)"',
        body,
        re.I,
    ):
        path, thumb = match.group(1), clean_thumb(match.group(2))
        if not thumb:
            continue
        page_url = "https://www.youjizz.com" + path
        if page_url in seen:
            continue
        seen.add(page_url)
        title = path.rsplit("/", 1)[-1].replace(".html", "").replace("-", " ")
        items.append(video_item("YouJizz", "youjizz", title, page_url, thumb, "", ""))
        if len(items) >= 40:
            break
    return attach_durations(items, body)


SOURCES = {
    "pornhub": ("Pornhub", pornhub_search),
    "xvideos": ("XVideos", xvideos_search),
    "xhamster": ("xHamster", xhamster_search),
    "xnxx": ("XNXX", xnxx_search),
    "redtube": ("RedTube", redtube_search),
    "eporner": ("Eporner", eporner_search),
    "xxxbunker": ("XXXBunker", xxxbunker_search),
    "tnaflix": ("TNAflix", tnaflix_search),
    "drtuber": ("DrTuber", drtuber_search),
    "pornone": ("PornOne", pornone_search),
    "okxxx": ("OK.xxx", okxxx_search),
    "porn00": ("Porn00", porn00_search),
    "xxxfiles": ("XXXFiles", xxxfiles_search),
    "xmoviesforyou": ("XMoviesForYou", xmoviesforyou_search),
    "whoreshub": ("WhoresHub", whoreshub_search),
    "yespornvip": ("YesPornVIP", yespornvip_search),
    "justporn": ("JustPorn", justporn_search),
    "spankbang": ("SpankBang", spankbang_search),
    "txxx": ("TXXX", txxx_search),
    "3movs": ("3Movs", threemovs_search),
    "hdzog": ("HDZog", hdzog_search),
    "hotmovs": ("HotMovs", hotmovs_search),
    "porngo": ("PornGo", porngo_search),
    "youjizz": ("YouJizz", youjizz_search),
    "xozilla": ("Xozilla", xozilla_search),
}


def run_search(query: str, source: str, page: int, tags: list[str] | None = None) -> dict:
    jobs = []
    if source in ("all", "", None):
        jobs = list(SOURCES.items())
    elif source in SOURCES:
        jobs = [(source, SOURCES[source])]
    else:
        jobs = list(SOURCES.items())

    items: list[dict] = []
    used: list[str] = []
    errors: list[str] = []
    tag_list = parse_tags(",".join(tags or []))
    content_tags, length = split_length_tags(tag_list)
    kind = feed_kind(query)
    if kind:
        send = query
    elif content_tags:
        send = focused_search_query(content_tags)
    elif length:
        send = "amateur"
    else:
        send = expand_search_query(query)
    if not (send or "").strip() or send.strip().lower() in LENGTH_TAGS:
        send = "amateur"
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(fn, send, page): name for name, (_label, fn) in jobs}
        for future in as_completed(futures):
            name = futures[future]
            try:
                found = [row for row in future.result() if allowed_item(row)]
                if found:
                    used.append(name)
                    items.extend(found)
            except Exception as error:
                errors.append(f"{name}: {error}")

    unique = []
    seen = set()
    for row in items:
        key = row.get("page") or row.get("id")
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    fetched = bool(unique)
    if kind:
        unique = interleave_by_source(unique)
    else:
        unique = rank_items(unique, query, content_tags)
    if length:
        unique = [row for row in unique if matches_length(row, length)]
    return {
        "query": query,
        "items": unique,
        "next": fetched,
        "sources": used,
        "date": today_stamp() if kind else None,
        "mode": kind or "search",
        "error": "; ".join(errors) if errors and not unique else None,
    }


def public_https(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return False
    return True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/search":
            self.handle_search(parsed)
            return
        if parsed.path == "/api/img":
            self.handle_image(parsed)
            return
        super().do_GET()

    def send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def handle_search(self, parsed):
        qs = parse_qs(parsed.query)
        query = (qs.get("q") or [""])[0].strip() or "amateur"
        source = (qs.get("source") or ["all"])[0]
        refresh = (qs.get("refresh") or ["0"])[0] == "1"
        tags = parse_tags((qs.get("tags") or [""])[0])
        try:
            page = max(0, int((qs.get("page") or ["0"])[0]))
        except ValueError:
            page = 0
        reason = blocked_query(query)
        if reason:
            self.send_json(400, {"error": reason, "items": []})
            return
        kind = feed_kind(query)
        if kind:
            if not refresh:
                cached = load_daily_cache(source, page, kind)
                if cached:
                    self.send_json(200, cached)
                    return
            try:
                payload = run_search(query, source, page, tags)
                save_daily_cache(source, page, payload, kind)
                self.send_json(200, payload)
            except Exception as error:
                try:
                    self.send_json(502, {"error": str(error), "items": []})
                except Exception:
                    print(f"search failed: {error}", flush=True)
            return
        cache_key = f"{source}|{query.lower()}|{','.join(tags)}|{page}"
        now = time.time()
        hit = CACHE.get(cache_key)
        if not refresh and hit and now - hit[0] < CACHE_TTL:
            self.send_json(200, hit[1])
            return
        try:
            payload = run_search(query, source, page, tags)
            CACHE[cache_key] = (now, payload)
            self.send_json(200, payload)
        except Exception as error:
            try:
                self.send_json(502, {"error": str(error), "items": []})
            except Exception:
                print(f"search failed: {error}", flush=True)

    def handle_image(self, parsed):
        target = clean_thumb((parse_qs(parsed.query).get("url") or [""])[0])
        if not public_https(target):
            self.send_error(400, "Blocked image url")
            return
        try:
            referer = (parse_qs(parsed.query).get("ref") or [""])[0]
            headers = {
                "User-Agent": BROWSER_UA,
                "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
            }
            if referer.startswith("https://"):
                parsed_ref = urlparse(referer)
                headers["Referer"] = f"{parsed_ref.scheme}://{parsed_ref.netloc}/"
            else:
                host = (urlparse(target).hostname or "").lower()
                if "xvideos" in host:
                    headers["Referer"] = "https://www.xvideos.com/"
                elif "xnxx" in host:
                    headers["Referer"] = "https://www.xnxx.com/"
                elif "xhamster" in host:
                    headers["Referer"] = "https://xhamster.com/"
                elif "rdtcdn" in host or "phncdn" in host or "redtube" in host:
                    headers["Referer"] = "https://www.redtube.com/"
                elif host:
                    headers["Referer"] = f"https://{host}/"
            request = Request(target, headers=headers)
            try:
                response = urlopen(request, timeout=20)
            except URLError as error:
                if "certificate" not in str(error).lower() and "SSL" not in str(error):
                    raise
                response = urlopen(request, timeout=20, context=SSL_LOOSE)
            try:
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                if "image" not in content_type and "octet-stream" not in content_type:
                    self.send_error(415, "Not an image")
                    return
                body = response.read(8_000_000)
            finally:
                response.close()
            self.send_response(200)
            self.send_header("Content-Type", content_type.split(";")[0])
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except (HTTPError, URLError, TimeoutError, ValueError):
            self.send_error(502, "Image fetch failed")

    def log_message(self, format, *args):
        if args and str(args[0]).startswith("GET /api/"):
            super().log_message(format, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("GitVidX", flush=True)
    print(f"This PC:  http://127.0.0.1:{PORT}", flush=True)
    print(f"Phone:    http://{lan_ip()}:{PORT}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    server.serve_forever()

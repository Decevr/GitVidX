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
DAILY_DIR = ROOT / ".cache"


def is_daily(query: str) -> bool:
    return (query or "").strip().lower() == DAILY_Q


def today_stamp() -> str:
    return date.today().isoformat()


def daily_cache_path(source: str, page: int) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "-", (source or "all").lower()).strip("-") or "all"
    return DAILY_DIR / f"daily-{today_stamp()}-{safe}-{page}.json"


def load_daily_cache(source: str, page: int) -> dict | None:
    path = daily_cache_path(source, page)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("date") == today_stamp() and data.get("items"):
            return data
    except Exception:
        return None
    return None


def save_daily_cache(source: str, page: int, payload: dict) -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = today_stamp()
    for old in DAILY_DIR.glob("daily-*.json"):
        if stamp not in old.name:
            try:
                old.unlink()
            except OSError:
                pass
    daily_cache_path(source, page).write_text(json.dumps(payload), encoding="utf-8")


STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "plus",
    "hair", "sex", "fuck", "video", "style", "position", "man", "guy",
    "view", "camera", "cam", "shot", "angle",
}

CATEGORY_ALIASES: dict[str, list[str]] = {
    "amateur": ["amateur"],
    "milf": ["milf"],
    "lesbian": ["lesbian"],
    "blonde": ["blonde", "blond"],
    "brunette": ["brunette"],
    "anal": ["anal"],
    "pov": ["pov"],
    "solo": ["solo", "masturbation"],
    "hardcore": ["hardcore"],
    "blowjob": ["blowjob", "blow job", "bj"],
    "creampie": ["creampie", "cream pie"],
    "big tits": ["big tits", "bigtits", "big boobs"],
    "asian": ["asian"],
    "latina": ["latina", "latin"],
    "threesome": ["threesome", "threesom"],
    "feet": ["feet", "foot fetish", "footjob"],
    "socks": ["socks", "sock", "sockjob", "sock fetish"],
    "cheating": ["cheating", "cheating wife"],
    "cuckold": ["cuckold", "cuckolding"],
    "teen": ["teen", "18 teen"],
    "step-sis": ["stepsister", "step sister", "step-sister", "stepsis", "step sis", "step-sis"],
    "homemade": ["homemade", "home made", "homemade amateur"],
    "onlyfans": ["onlyfans", "only fans", "only-fans"],
    "ai": ["ai generated", "ai porn", "ai generated porn"],
    "missionary": ["missionary"],
    "doggy": ["doggy", "doggy style", "doggystyle", "from behind"],
    "cowgirl": ["cowgirl", "riding"],
    "reverse cowgirl": ["reverse cowgirl", "reversecowgirl"],
    "spooning": ["spooning", "spoon"],
    "standing": ["standing", "standing sex", "standing fuck"],
    "69": ["69", "sixty nine"],
    "prone bone": ["prone bone", "pronebone"],
    "mating press": ["mating press", "matingpress"],
    "lotus": ["lotus", "lotus position"],
    "piledriver": ["piledriver"],
    "butterfly": ["butterfly", "butterfly position"],
    "amazon": ["amazon", "amazon position"],
    "wheelbarrow": ["wheelbarrow"],
    "anvil": ["anvil", "anvil position"],
    "facesitting": ["facesitting", "face sitting", "queening"],
    "scissoring": ["scissoring", "scissor"],
    "sideways": ["sideways", "side fuck", "on the side"],
    "legs up": ["legs up", "legs in the air"],
    "bent over": ["bent over", "bend over"],
    "full nelson": ["full nelson"],
    "against wall": ["against the wall", "wall sex", "pinned to the wall"],
    "chair": ["chair sex", "chair fuck"],
    "michigan": ["michigan", "michigan sex"],
    "slipped in": ["slipped it in", "accidentally slipped it in", "accidentally slipped in", "accidental slip"],
    "redhead": ["redhead", "red hair", "ginger"],
    "black hair": ["black hair", "dark hair"],
    "auburn": ["auburn"],
    "platinum": ["platinum blonde", "platinum"],
    "grey": ["grey hair", "gray hair", "silver hair"],
    "pink hair": ["pink hair"],
    "blue hair": ["blue hair"],
    "purple hair": ["purple hair"],
    "cellphone": ["cellphone", "phone video", "mobile video"],
    "snapchat": ["snapchat"],
    "hotel": ["hotel sex", "hotel"],
    "motel": ["motel sex", "motel"],
    "car": ["car sex", "car fuck"],
    "public": ["public sex", "public"],
    "sneaky": ["sneaky sex", "sneaky"],
    "quickie": ["quickie"],
    "tramp stamp": ["tramp stamp"],
    "delivery guy": ["delivery guy", "delivery man"],
    "maintenance man": ["maintenance man", "handyman"],
    "fly on the wall": ["fly on the wall", "fly-on-the-wall", "third person camera"],
    "third person": ["third person", "third person view"],
    "close up": ["close up", "close-up", "closeup"],
    "full body": ["full body", "fullbody"],
    "overhead": ["overhead view", "top down", "birds eye"],
    "low angle": ["low angle"],
    "side view": ["side view", "side angle"],
    "behind camera": ["camera from behind", "shot from behind"],
    "face cam": ["face cam", "facecam"],
    "looking at camera": ["looking at camera", "looks at camera"],
    "mirror": ["mirror fuck", "mirror sex"],
    "handheld": ["handheld camera", "handheld"],
    "tripod": ["tripod"],
    "gopro": ["gopro"],
    "selfie cam": ["selfie", "front camera"],
    "two camera": ["two camera", "dual camera", "multi cam"],
    "cinematic": ["cinematic"],
    "over the shoulder": ["over the shoulder"],
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
    if is_daily(query):
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
            if len(words) >= 6:
                return " ".join(words)
    return " ".join(words)


def distinctive_tokens(query: str) -> list[str]:
    phrase = expand_search_query(query)
    tokens: list[str] = []
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
    title, page, compact = item_text(item)
    tokens = distinctive_tokens(tag)
    if tokens:
        return any(token_in_item(token, title, page, compact) for token in tokens)
    return relevance_score(item, ranking_terms(tag)) >= 6


def rank_items(items: list[dict], query: str, tags: list[str] | None = None) -> list[dict]:
    tag_list = [tag for tag in (tags or []) if tag]
    if tag_list:
        terms = list(dict.fromkeys(term for tag in tag_list for term in ranking_terms(tag)))
        scored = []
        for item in items:
            hits = sum(1 for tag in tag_list if tag_matched(item, tag))
            score = relevance_score(item, terms)
            scored.append((hits, score, item))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        total = len(tag_list)
        full = [item for hits, _score, item in scored if hits >= total]
        almost = [item for hits, _score, item in scored if hits >= max(1, total - 1)]
        some = [item for hits, score, item in scored if hits > 0]
        if len(full) >= 6:
            return full
        if len(almost) >= 6:
            return almost
        return some
    tokens = distinctive_tokens(query)
    terms = ranking_terms(query)
    scored = []
    for item in items:
        title, page, compact = item_text(item)
        hit_count = sum(1 for token in tokens if token_in_item(token, title, page, compact)) if tokens else 0
        score = relevance_score(item, terms)
        scored.append((hit_count, score, item))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    needed = max(1, (len(tokens) + 1) // 2) if tokens else 1
    strong = [item for hits, score, item in scored if hits >= needed or score >= 8]
    if strong:
        return strong
    return [item for hits, score, item in scored if hits > 0 or score > 0]


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
        "thumb": thumb,
        "embed": embed,
        "duration": clean_duration(duration),
    }


def allowed_item(row: dict) -> bool:
    blob = " ".join(str(row.get(key) or "") for key in ("title", "page", "url", "provider"))
    if blocked_query(blob):
        return False
    return not any(host_blocked(row.get(key) or "") for key in ("page", "url", "thumb", "embed"))


def pornhub_search(query: str, page: int) -> list[dict]:
    if is_daily(query):
        params = urlencode({"thumbsize": "large", "ordering": "featured", "page": page + 1})
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
    if is_daily(query):
        params["ordering"] = "featured"
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
            "query": "" if is_daily(query) else query,
            "per_page": 20,
            "page": page + 1,
            "thumbsize": "medium",
            "order": "top-weekly" if is_daily(query) else "latest",
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
    return url


def xvideos_search(query: str, page: int) -> list[dict]:
    if is_daily(query):
        target = "https://www.xvideos.com/" if page == 0 else f"https://www.xvideos.com/new/{page + 1}"
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
    if is_daily(query):
        target = "https://www.xnxx.com/todays-selection" if page == 0 else f"https://www.xnxx.com/todays-selection/{page}"
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
    if is_daily(query):
        suffix = "" if page == 0 else f"/{page + 1}"
        target = f"https://xhamster.com/best/daily{suffix}"
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
    if is_daily(query):
        extra = f"/{page + 1}" if page else ""
        target = f"https://xxxbunker.com/{extra.lstrip('/')}" if extra else "https://xxxbunker.com/"
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
    if is_daily(query):
        extra = f"?page={page + 1}" if page else ""
        target = f"https://www.tnaflix.com/{extra}"
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
    if is_daily(query):
        target = "https://www.drtuber.com/" if page == 0 else f"https://www.drtuber.com/latest-updates/{page + 1}"
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
    if is_daily(query):
        target = "https://www.pornone.com/" if page == 0 else f"https://www.pornone.com/{page + 1}/"
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
    if is_daily(query):
        target = "https://ok.xxx/" if page == 0 else f"https://ok.xxx/latest-updates/{page + 1}/"
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
    if is_daily(query):
        target = "https://www.porn00.org/latest/" if page == 0 else f"https://www.porn00.org/latest/{page + 1}/"
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
    if is_daily(query):
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
    if is_daily(query):
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
    if is_daily(query):
        target = "https://www.whoreshub.com/" if page == 0 else f"https://www.whoreshub.com/latest-updates/{page + 1}/"
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
    if is_daily(query):
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
    if is_daily(query):
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
    if is_daily(query):
        send = query
    elif tag_list:
        send = combine_search_query(tag_list)
    else:
        send = expand_search_query(query)
    if not (send or "").strip():
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
    if is_daily(query):
        unique = interleave_by_source(unique)
    else:
        unique = rank_items(unique, query, tag_list)
    return {
        "query": query,
        "items": unique,
        "next": bool(unique) and not is_daily(query),
        "sources": used,
        "date": today_stamp() if is_daily(query) else None,
        "mode": "daily" if is_daily(query) else "search",
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
        if is_daily(query):
            if not refresh:
                cached = load_daily_cache(source, page)
                if cached:
                    self.send_json(200, cached)
                    return
            try:
                payload = run_search(query, source, page, tags)
                save_daily_cache(source, page, payload)
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
        target = (parse_qs(parsed.query).get("url") or [""])[0]
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
                elif host:
                    headers["Referer"] = f"https://{host}/"
            request = Request(target, headers=headers)
            with urlopen(request, timeout=20) as response:
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                if "image" not in content_type and "octet-stream" not in content_type:
                    self.send_error(415, "Not an image")
                    return
                body = response.read(8_000_000)
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

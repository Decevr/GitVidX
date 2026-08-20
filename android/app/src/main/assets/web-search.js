/* Client search for GitHub Pages / home-screen PWA (no Python server). */
(function () {
  const DAILY_Q = "__daily__";
  const STOP = new Set(["a","an","the","and","or","of","to","in","for","on","with","plus","hair","sex","fuck","video","style","position","man","guy","view","camera","cam","shot","angle"]);
  const PHRASES = {
    amateur: "amateur", milf: "milf", lesbian: "lesbian", blonde: "blonde", brunette: "brunette",
    anal: "anal", pov: "pov", solo: "solo", hardcore: "hardcore", blowjob: "blowjob",
    creampie: "creampie", "big tits": "big tits", "tan line": "tan lines",
    "small tits": "small tits", "medium tits": "medium tits", "large tits": "huge tits",
    "natural tits": "natural tits", "perky tits": "perky tits", "large ass": "big ass",
    "round ass": "round ass", petite: "petite", curvy: "curvy", thick: "thick", pawg: "pawg",
    cmnf: "cmnf", cfnm: "cfnm", "lap dance": "lap dance", striptease: "striptease",
    oil: "oiled", massage: "massage", storyline: "storyline",
    "full movie": "full movie", "full scene": "full scene",
    asian: "asian", latina: "latina",
    threesome: "threesome", feet: "feet", socks: "socks", cheating: "cheating wife",
    cuckold: "cuckold", teen: "teen", "step-sis": "stepsister", homemade: "homemade",
    onlyfans: "onlyfans", ai: "ai generated", missionary: "missionary", doggy: "doggy style",
    cowgirl: "cowgirl", "reverse cowgirl": "reverse cowgirl", spooning: "spooning",
    standing: "standing sex", "69": "69", "prone bone": "prone bone", "mating press": "mating press",
    lotus: "lotus position", piledriver: "piledriver", butterfly: "butterfly position",
    amazon: "amazon position", wheelbarrow: "wheelbarrow", anvil: "anvil position",
    facesitting: "facesitting", scissoring: "scissoring", sideways: "sideways fuck",
    "legs up": "legs up", "bent over": "bent over", "full nelson": "full nelson",
    "against wall": "against the wall", chair: "chair sex", michigan: "michigan",
    "slipped in": "slipped it in", redhead: "redhead", "black hair": "black hair",
    auburn: "auburn", platinum: "platinum blonde", grey: "grey hair", "pink hair": "pink hair",
    "blue hair": "blue hair", "purple hair": "purple hair", cellphone: "cellphone video",
    snapchat: "snapchat", hotel: "hotel sex", motel: "motel sex", car: "car sex",
    public: "public sex", sneaky: "sneaky sex", quickie: "quickie", "tramp stamp": "tramp stamp",
    "delivery guy": "delivery guy", "maintenance man": "maintenance man",
    "co-worker": "coworker", babysitter: "babysitter", cosplay: "cosplay", parody: "parody",
    "fly on the wall": "fly on the wall", "third person": "third person view",
    "close up": "close up", "full body": "full body", overhead: "overhead view",
    "low angle": "low angle", "side view": "side view", "behind camera": "from behind camera",
    "face cam": "face cam", "looking at camera": "looking at camera", mirror: "mirror sex",
    handheld: "handheld camera", tripod: "tripod camera", gopro: "gopro",
    "selfie cam": "selfie", "two camera": "two camera", cinematic: "cinematic",
    "over the shoulder": "over the shoulder", "wide shot": "wide shot"
  };
  const ALIASES = {
    amateur: ["amateur", "real amateur"], milf: ["milf"],
    lesbian: ["lesbian", "lesbians", "girl on girl"],
    blonde: ["blonde", "blond", "blonde hair", "blond hair"],
    brunette: ["brunette", "brown hair", "brown haired"],
    anal: ["anal"], pov: ["pov", "point of view"],
    solo: ["solo", "masturbation", "masturbating"], hardcore: ["hardcore"],
    blowjob: ["blowjob", "blow job", "bj", "cock sucking"],
    creampie: ["creampie", "cream pie"],
    "big tits": ["big tits", "bigtits", "big boobs", "huge tits", "huge boobs", "big breasts"],
    "tan line": ["tan line", "tanline", "tan lines", "tanlines"],
    "small tits": ["small tits", "small tit", "tiny tits", "tiny tit", "little tits", "small boobs", "tiny boobs", "little boobs", "small breasts", "tiny breasts", "flat chest", "small chest", "petite tits", "a cup"],
    "medium tits": ["medium tits", "medium boobs", "medium breasts", "average tits", "c cup", "medium sized tits"],
    "large tits": ["large tits", "huge tits", "big tits", "giant tits", "massive tits", "big boobs", "huge boobs", "massive boobs", "giant boobs", "big breasts", "huge breasts", "large breasts", "big naturals", "busty", "bigtits"],
    "natural tits": ["natural tits", "natural breasts", "natural boobs", "naturals", "real tits"],
    "perky tits": ["perky tits", "perky breasts", "perky boobs"],
    "large ass": ["large ass", "big ass", "huge ass", "fat ass", "phat ass", "big booty", "huge booty", "bubble butt", "big butt"],
    "round ass": ["round ass", "round booty", "peach ass", "bubble butt"],
    petite: ["petite"], curvy: ["curvy", "curvy body"], thick: ["thick", "thicc"], pawg: ["pawg"],
    cmnf: ["cmnf", "clothed male naked female"], cfnm: ["cfnm", "clothed female naked male"],
    "lap dance": ["lap dance", "lapdance"], striptease: ["striptease", "strip tease"],
    oil: ["oiled", "oil massage", "oiled up", "oily"], massage: ["massage"],
    storyline: ["storyline", "story line", "plot"],
    "full movie": ["full movie", "full length", "feature length"],
    "full scene": ["full scene", "complete scene"],
    asian: ["asian"], latina: ["latina", "latin", "hispanic"],
    threesome: ["threesome", "threesom", "ffm", "mmf", "3some"],
    feet: ["feet", "foot fetish", "footjob", "soles"],
    socks: ["socks", "sock", "sockjob", "sock fetish", "ankle socks", "white socks"],
    cheating: ["cheating", "cheating wife", "cheats", "affair"],
    cuckold: ["cuckold", "cuckolding", "cuck"],
    teen: ["teen", "18 teen", "18 year", "barely 18"],
    "step-sis": ["stepsister", "step sister", "step-sister", "stepsis", "step sis", "step-sis"],
    homemade: ["homemade", "home made", "homemade amateur", "real homemade"],
    onlyfans: ["onlyfans", "only fans", "only-fans"],
    ai: ["ai generated", "ai porn", "ai generated porn", "artificial intelligence"],
    missionary: ["missionary"], doggy: ["doggy", "doggy style", "doggystyle"],
    cowgirl: ["cowgirl", "cow girl"], "reverse cowgirl": ["reverse cowgirl", "reversecowgirl"],
    spooning: ["spooning", "spoon fuck"], standing: ["standing sex", "standing fuck", "standing doggy"],
    "69": ["69", "sixty nine", "sixtynine"], "prone bone": ["prone bone", "pronebone"],
    "mating press": ["mating press", "matingpress"], lotus: ["lotus position", "lotus pose"],
    piledriver: ["piledriver", "pile driver"], butterfly: ["butterfly position", "butterfly pose"],
    amazon: ["amazon position", "amazon pose"], wheelbarrow: ["wheelbarrow"],
    anvil: ["anvil position", "anvil pose"],
    facesitting: ["facesitting", "face sitting", "queening"], scissoring: ["scissoring", "scissor"],
    sideways: ["sideways", "side fuck", "on the side"],
    "legs up": ["legs up", "legs in the air", "legs over"],
    "bent over": ["bent over", "bend over", "bending over"], "full nelson": ["full nelson"],
    "against wall": ["against the wall", "wall sex", "pinned to the wall", "against wall"],
    chair: ["chair sex", "chair fuck", "on the chair"],
    michigan: ["michigan", "michigan sex", "michigan position"],
    "slipped in": ["slipped it in", "accidentally slipped it in", "accidentally slipped in", "accidental slip"],
    redhead: ["redhead", "red hair", "red haired", "ginger"],
    "black hair": ["black hair", "black haired", "dark hair", "jet black hair"],
    auburn: ["auburn", "auburn hair"],
    platinum: ["platinum blonde", "platinum blond", "platinum hair", "platinum"],
    grey: ["grey hair", "gray hair", "silver hair", "granny hair"],
    "pink hair": ["pink hair", "pink haired"], "blue hair": ["blue hair", "blue haired"],
    "purple hair": ["purple hair", "purple haired"],
    cellphone: ["cellphone", "cell phone", "phone video", "mobile video", "iphone video"],
    snapchat: ["snapchat", "snap chat"],
    hotel: ["hotel sex", "hotel room", "hotel fuck"], motel: ["motel sex", "motel room", "motel fuck"],
    car: ["car sex", "car fuck", "in the car", "backseat", "back seat"],
    public: ["public sex", "public fuck", "in public"], sneaky: ["sneaky sex", "sneaky fuck", "sneaky"],
    quickie: ["quickie", "quick fuck"], "tramp stamp": ["tramp stamp", "lower back tattoo"],
    "delivery guy": ["delivery guy", "delivery man", "pizza guy"],
    "maintenance man": ["maintenance man", "handyman", "repair man", "plumber"],
    "co-worker": ["coworker", "co worker", "co-worker", "office sex", "office fuck", "at work", "colleague", "coworkers"],
    babysitter: ["babysitter", "baby sitter", "baby-sitter", "nanny"],
    cosplay: ["cosplay", "cos play", "costume play"],
    parody: ["parody", "porn parody", "xxx parody", "spoof"],
    "fly on the wall": ["fly on the wall", "fly-on-the-wall", "third person camera"],
    "third person": ["third person", "third person view"],
    "close up": ["close up", "close-up", "closeup"], "full body": ["full body", "fullbody"],
    overhead: ["overhead view", "top down", "birds eye"], "low angle": ["low angle", "low-angle"],
    "side view": ["side view", "side angle"],
    "behind camera": ["camera from behind", "shot from behind", "from behind camera"],
    "face cam": ["face cam", "facecam"],
    "looking at camera": ["looking at camera", "looks at camera", "look at camera"],
    mirror: ["mirror fuck", "mirror sex", "in the mirror"],
    handheld: ["handheld camera", "handheld"], tripod: ["tripod", "tripod camera"],
    gopro: ["gopro", "go pro"], "selfie cam": ["selfie", "front camera", "selfie cam"],
    "two camera": ["two camera", "dual camera", "multi cam"], cinematic: ["cinematic"],
    "over the shoulder": ["over the shoulder", "over-the-shoulder"],
    "wide shot": ["wide shot", "wide angle"]
  };
  const WEAK = new Set(["black","dark","red","pink","blue","purple","grey","gray","silver","large","small","medium","big","huge","tiny","little","round","full","close","wide","low","side","third","two","over","looking","from","behind","against","natural","perky","fake","tits","tit","boobs","boob","ass","butt","booty","breasts","breast"]);
  const PHRASE_ONLY = new Set(["amazon","butterfly","black hair","pink hair","blue hair","purple hair","looking at camera","over the shoulder","fly on the wall","third person","behind camera","delivery guy","maintenance man","tramp stamp","tan line","anvil","lotus","co-worker"]);
  const NEGATE = {
    "small tits": ["huge tits","massive tits","enormous tits","giant tits","big tits","large tits","huge boobs","massive boobs","big boobs"],
    "large tits": ["small tits","tiny tits","flat chest","little tits","small boobs","tiny boobs"],
    "big tits": ["small tits","tiny tits","flat chest","little tits","small boobs","tiny boobs"],
    "medium tits": ["huge tits","massive tits","giant tits","tiny tits","flat chest"],
    "large ass": ["flat ass","no ass","skinny ass"],
    "round ass": ["flat ass"],
    petite: ["bbw","ssbbw","plus size"],
    "natural tits": ["fake tits","fake boobs","implants","fake breasts"],
    blonde: ["brunette","redhead","ginger","black hair","brown hair"],
    brunette: ["blonde","blond","redhead","ginger","platinum"],
    redhead: ["blonde","blond","brunette","black hair","platinum"],
    "black hair": ["blonde","blond","redhead","ginger","platinum"],
    platinum: ["brunette","redhead","ginger","black hair","brown hair"]
  };
  const BLOCK = /\b(child|children|kid|kids|toddler|infant|baby|babies|minor|minors|underage|under[\s-]?age|preteen|pre[\s-]?teen|loli|lolita|shota|pedo|paedo|jailbait|young[\s-]?girl|little[\s-]?girl|(1[0-7]|[0-9])\s*(yo|yr|years?\s*old)|leak|leaked|leaks|stolen|hacked|fappening|celebgate|revenge\s*porn|non[\s-]?consensual|without\s+consent|no\s+consent|hidden\s*cam|spy\s*cam|voyeur|creepshot|upskirt|downblouse|passed\s+out|unconscious|drugged|sleeping\s+nude|rape|raped|forced|blackmail|deepnude|undress)\b/i;
  const HOST_BITS = ["leak","leaked","thothub","fappening","celebgate","nudel","coomer","kemono","simpcity","fapello","cyberdrop"];

  const LENGTH = new Set(["short", "long"]);
  const SHORT_MAX = 10 * 60;
  const LONG_MIN = 20 * 60;
  function isDaily(q) { return String(q || "").trim().toLowerCase() === DAILY_Q; }
  function splitLength(tags) {
    const length = tags.find((tag) => LENGTH.has(tag)) || "";
    return { content: tags.filter((tag) => !LENGTH.has(tag)), length };
  }
  function durationSeconds(row) {
    const text = String(row && row.duration || "").trim();
    if (!text) return 0;
    if (/^\d{1,5}$/.test(text)) {
      const total = Number(text);
      return total > 0 && total <= 12 * 3600 ? total : 0;
    }
    const clock = text.match(/^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$/);
    if (clock) {
      const hour = clock[1] ? Number(clock[1]) : 0;
      return hour * 3600 + Number(clock[2]) * 60 + Number(clock[3]);
    }
    const mins = text.match(/^(\d{1,3})\s*(?:min|mins|minutes)\b/i);
    return mins ? Number(mins[1]) * 60 : 0;
  }
  function matchesLength(row, length) {
    if (!length) return true;
    const secs = durationSeconds(row);
    if (!secs) return false;
    if (length === "short") return secs <= SHORT_MAX;
    if (length === "long") return secs >= LONG_MIN;
    return true;
  }
  function expand(q) {
    if (isDaily(q)) return q;
    const key = String(q || "").trim().toLowerCase().replace(/[\s_]+/g, " ");
    return PHRASES[key] || String(q || "").trim();
  }
  function enc(value) { return encodeURIComponent(value).replace(/%20/g, "+"); }
  function today() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  function hash(text) {
    let h = 5381;
    const s = String(text || "");
    for (let i = 0; i < s.length; i += 1) h = Math.imul(h, 33) ^ s.charCodeAt(i);
    return (h >>> 0).toString(16).padStart(8, "0");
  }
  function item(provider, source, title, page, thumb, embed, duration) {
    const pageUrl = page || "";
    return {
      id: `${source}-${hash(pageUrl || title).slice(0, 16)}`,
      provider, source,
      title: String(title || "").slice(0, 180),
      page: pageUrl, url: pageUrl,
      thumb: cleanThumb(thumb || ""),
      embed: embed || "",
      duration: duration || ""
    };
  }
  function cleanThumb(url) {
    let value = url || "";
    if (value.startsWith("//")) value = "https:" + value;
    const low = value.toLowerCase();
    if (["blank.gif","lightbox-blank","placeholder","pixel.gif","1x1"].some((b) => low.includes(b))) return "";
    return value.replace("ei-ph.rdtcdn.com", "ei.phncdn.com").replace(".rdtcdn.com", ".phncdn.com");
  }
  function blocked(text) { return BLOCK.test(text || ""); }
  function hostBlocked(url) {
    try {
      const host = new URL(url).hostname.toLowerCase();
      return HOST_BITS.some((b) => host.includes(b));
    } catch { return Boolean(url); }
  }
  function allowed(row) {
    const blob = [row.title, row.page, row.url].join(" ");
    if (blocked(blob)) return false;
    return !hostBlocked(row.page) && !hostBlocked(row.url);
  }
  function combine(tags) {
    const words = [];
    const seen = new Set();
    for (const tag of tags) {
      for (const word of expand(tag).split(/\s+/)) {
        const key = word.toLowerCase();
        if (!key || STOP.has(key) || seen.has(key)) continue;
        seen.add(key);
        words.push(word);
        if (words.length >= 5) return words.join(" ");
      }
    }
    return words.join(" ");
  }
  const STYLE = new Set(["cellphone","snapchat","homemade","amateur","onlyfans","ai","pov","fly on the wall","third person","close up","full body","overhead","low angle","side view","behind camera","face cam","looking at camera","mirror","handheld","tripod","gopro","selfie cam","two camera","cinematic","over the shoulder","wide shot"]);
  function focused(tags) {
    const spec = (tag) => {
      let score = tokens(tag).reduce((n, t) => n + t.length, 0);
      if (expand(tag).includes(" ")) score += 4;
      if (STYLE.has(String(tag || "").trim().toLowerCase().replace(/[\s_]+/g, " "))) score -= 8;
      return score;
    };
    const ranked = [...tags].sort((a, b) => spec(b) - spec(a));
    const phrases = [];
    const seen = new Set();
    for (const tag of ranked.slice(0, 2)) {
      const phrase = expand(tag);
      const key = phrase.toLowerCase();
      if (phrase && !seen.has(key)) {
        seen.add(key);
        phrases.push(phrase);
      }
    }
    return phrases.join(" ") || combine(ranked.slice(0, 3));
  }
  function aliases(tag) {
    const key = String(tag || "").trim().toLowerCase().replace(/[\s_]+/g, " ");
    const extra = PHRASE_ONLY.has(key) ? [] : [key];
    return [...new Set([...(ALIASES[key] || []), ...extra, expand(tag), PHRASES[key] || ""])].filter(Boolean);
  }
  function tokensNear(title, toks) {
    if (toks.length <= 1) return true;
    const starts = [];
    for (const tok of toks) {
      const m = title.match(new RegExp(`\\b${tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`));
      if (!m || m.index == null) return true;
      starts.push(m.index);
    }
    return Math.max(...starts) - Math.min(...starts) <= 28 + toks.reduce((n, t) => n + t.length, 0);
  }
  function aliasHitsOne(title, compact, alias) {
    const phrase = norm(alias);
    if (!phrase) return false;
    if (!phrase.includes(" ")) {
      const re = new RegExp(`\\b${phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`);
      if (re.test(title)) return true;
    } else if (title.includes(phrase)) return true;
    const glued = phrase.replace(/ /g, "");
    if (glued.length >= 5 && compact.includes(glued)) return true;
    const words = phrase.split(/\s+/).filter(Boolean);
    const toks = words.filter((t) => t && !STOP.has(t) && (t.length >= 2 || t === "ai"));
    if (!toks.length) return false;
    if (words.length > 1 && toks.length === 1) return false;
    if (toks.every((t) => WEAK.has(t) || t.length < 4)) return false;
    if (!toks.every((t) => tokenIn(t, title, ""))) return false;
    return tokensNear(title, toks);
  }
  function aliasHitsTitle(title, tag) {
    const compact = title.replace(/ /g, "");
    return aliases(tag).some((alias) => aliasHitsOne(title, compact, alias));
  }
  function tokens(q) {
    const key = String(q || "").trim().toLowerCase().replace(/[\s_]+/g, " ");
    const fromKey = key.replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/)
      .filter((t) => t && !STOP.has(t) && (t.length >= 2 || t === "ai"));
    if (fromKey.length) return fromKey;
    return expand(q).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/)
      .filter((t) => t && !STOP.has(t) && (t.length >= 2 || t === "ai"));
  }
  function norm(s) { return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(); }
  function tokenIn(token, title, page) {
    const compact = title.replace(/ /g, "");
    if (token === "ai") return /\bai\b/.test(title) || /\bai\b/.test(page);
    const re = new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`);
    if (re.test(title)) return true;
    if (token.length >= 4 && compact.includes(token)) return true;
    return re.test(page);
  }
  function tagMatched(row, tag) {
    const title = norm(row.title);
    const compact = title.replace(/ /g, "");
    const key = String(tag || "").trim().toLowerCase().replace(/[\s_]+/g, " ");
    const negs = NEGATE[key] || [];
    if (negs.some((neg) => title.includes(neg)) && !aliasHitsTitle(title, tag)) return false;
    if (aliasHitsTitle(title, tag)) return true;
    if (PHRASE_ONLY.has(key)) return false;
    const list = tokens(tag);
    const strong = list.filter((t) => !WEAK.has(t) && t.length >= 4);
    if (!strong.length) return false;
    if (list.length && list.every((t) => tokenIn(t, title, ""))) return tokensNear(title, list);
    return false;
  }
  function tagStrength(row, tag) {
    if (!tagMatched(row, tag)) return 0;
    const title = norm(row.title);
    const compact = title.replace(/ /g, "");
    for (const alias of aliases(tag)) {
      const phrase = norm(alias);
      if (phrase && title.includes(phrase)) return 3;
      const glued = phrase.replace(/ /g, "");
      if (phrase && glued.length >= 5 && compact.includes(glued)) return 3;
    }
    return 2;
  }
  function queryAsTags(query) {
    const key = String(query || "").trim().toLowerCase().replace(/[\s_]+/g, " ");
    if (ALIASES[key] || PHRASES[key]) return [key];
    const blob = norm(query);
    if (!blob) return [];
    const found = [];
    const names = Object.keys(ALIASES).sort((a, b) => b.length - a.length);
    for (const name of names) {
      for (const alias of aliases(name)) {
        const phrase = norm(alias);
        if (!phrase) continue;
        const re = new RegExp(`\\b${phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`);
        if (re.test(blob)) {
          found.push(name);
          break;
        }
      }
      if (found.length >= 4) break;
    }
    return found;
  }
  function rank(items, query, tags) {
    let tagList = (tags || []).filter(Boolean);
    if (!tagList.length) tagList = queryAsTags(query);
    if (tagList.length) {
      const scored = items.map((row) => {
        const hits = tagList.reduce((n, tag) => n + (tagMatched(row, tag) ? 1 : 0), 0);
        const strength = tagList.reduce((n, tag) => n + tagStrength(row, tag), 0);
        return { hits, strength, row };
      }).sort((a, b) => b.hits - a.hits || b.strength - a.strength);
      const total = tagList.length;
      const full = scored.filter((s) => s.hits >= total).map((s) => s.row);
      const almost = scored.filter((s) => s.hits >= Math.max(1, total - 1)).map((s) => s.row);
      const some = scored.filter((s) => s.hits > 0).map((s) => s.row);
      if (full.length) return full;
      if (almost.length) return almost;
      return some;
    }
    const list = tokens(query);
    const needed = !list.length ? 0 : (list.length <= 3 ? list.length : Math.max(2, Math.ceil(list.length * 2 / 3)));
    const scored = items.map((row) => {
      const title = norm(row.title);
      const titleHits = list.reduce((n, t) => n + (tokenIn(t, title, "") ? 1 : 0), 0);
      return { titleHits, row };
    }).sort((a, b) => b.titleHits - a.titleHits);
    if (!list.length) return scored.map((s) => s.row);
    const strong = scored.filter((s) => s.titleHits >= needed).map((s) => s.row);
    if (strong.length) return strong;
    if (needed > 1) {
      const softer = scored.filter((s) => s.titleHits >= needed - 1).map((s) => s.row);
      if (softer.length) return softer;
    }
    return scored.filter((s) => s.titleHits > 0).map((s) => s.row);
  }

  async function fetchText(url) {
    const tries = [
      url,
      "https://corsproxy.io/?" + encodeURIComponent(url),
      "https://api.allorigins.win/raw?url=" + encodeURIComponent(url)
    ];
    for (const target of tries) {
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 12000);
        const res = await fetch(target, {
          signal: ctrl.signal,
          headers: { Accept: "text/html,application/json;q=0.9,*/*;q=0.8" }
        });
        clearTimeout(timer);
        if (!res.ok) continue;
        const text = await res.text();
        if (text && text.length > 80) return text;
      } catch {
        /* try next */
      }
    }
    return "";
  }

  function jsonList(text, key) {
    try {
      const data = JSON.parse(text);
      return data[key] || data.videos || [];
    } catch { return []; }
  }

  function allMatches(re, body) {
    const out = [];
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(body))) out.push(m);
    return out;
  }

  async function pornhub(q, page, daily) {
    const url = daily
      ? `https://www.pornhub.com/webmasters/search?thumbsize=large&ordering=featured&page=${page + 1}`
      : `https://www.pornhub.com/webmasters/search?search=${enc(q)}&thumbsize=large&page=${page + 1}`;
    return jsonList(await fetchText(url), "videos").map((row) => {
      const pageUrl = row.url || "";
      let embed = "";
      const at = pageUrl.indexOf("viewkey=");
      if (at >= 0) embed = "https://www.pornhub.com/embed/" + pageUrl.slice(at + 8).split("&")[0];
      return item("Pornhub", "pornhub", row.title, pageUrl, row.default_thumb || row.thumb, embed, row.duration);
    });
  }
  async function redtube(q, page, daily) {
    const url = daily
      ? `https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&ordering=featured&thumbsize=medium&page=${page + 1}`
      : `https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&search=${enc(q)}&thumbsize=medium&page=${page + 1}`;
    return jsonList(await fetchText(url), "videos").map((wrap) => {
      const row = wrap.video || wrap;
      const id = String(row.video_id || "");
      return item("RedTube", "redtube", row.title, row.url, row.default_thumb || row.thumb, id ? `https://embed.redtube.com/?id=${id}` : "", row.duration);
    });
  }
  async function eporner(q, page, daily) {
    const url = daily
      ? `https://www.eporner.com/api/v2/video/search/?query=&per_page=20&page=${page + 1}&order=top-weekly&gay=0&lq=1&format=json`
      : `https://www.eporner.com/api/v2/video/search/?query=${enc(q)}&per_page=20&page=${page + 1}&order=latest&gay=0&lq=1&format=json`;
    return jsonList(await fetchText(url), "videos").map((row) => {
      let thumb = "";
      if (row.default_thumb && typeof row.default_thumb === "object") thumb = row.default_thumb.src || "";
      else thumb = row.default_thumb || "";
      const embed = row.embed || (row.id ? `https://www.eporner.com/embed/${row.id}` : "");
      return item("Eporner", "eporner", row.title, row.url, thumb, embed, row.length_min);
    });
  }
  async function htmlPair(url, provider, source, re, prefix) {
    const body = await fetchText(url);
    const seen = new Set();
    const items = [];
    for (const m of allMatches(re, body)) {
      const path = m[1];
      const thumb = cleanThumb(m[m.length - 1] || "");
      const pageUrl = path.startsWith("http") ? path.split("?")[0] : prefix + path;
      if (!thumb || seen.has(pageUrl)) continue;
      seen.add(pageUrl);
      const title = (m.length > 3 && m[2] ? m[2] : pageUrl.split("/").pop()).replace(/[-_]/g, " ");
      items.push(item(provider, source, title, pageUrl, thumb, "", ""));
      if (items.length >= 40) break;
    }
    return items;
  }

  const SITES = {
    pornhub, redtube, eporner,
    async xvideos(q, page, daily) {
      const url = daily ? (page === 0 ? "https://www.xvideos.com/" : `https://www.xvideos.com/new/${page + 1}`)
        : `https://www.xvideos.com/?k=${enc(q)}&p=${page}`;
      return htmlPair(url, "XVideos", "xvideos", /href="(\/video[^"]+)"[\s\S]{0,900}?data-src="(https:[^"]+)"/gi, "https://www.xvideos.com");
    },
    async xnxx(q, page, daily) {
      const extra = page === 0 ? "" : `/${page}`;
      const url = daily ? `https://www.xnxx.com/todays-selection${extra}` : `https://www.xnxx.com/search/${enc(q)}${extra}`;
      return htmlPair(url, "XNXX", "xnxx", /href="(\/video-[^"]+)"[\s\S]{0,900}?data-src="(https:[^"]+)"/gi, "https://www.xnxx.com");
    },
    async xhamster(q, page, daily) {
      const url = daily ? (page === 0 ? "https://xhamster.com/best/daily" : `https://xhamster.com/best/daily/${page + 1}`)
        : `https://xhamster.com/search/${enc(q)}${page === 0 ? "" : `?page=${page + 1}`}`;
      return htmlPair(url, "xHamster", "xhamster", /href="(https:\/\/xhamster\.com\/videos\/[^"]+)"[^>]*>[\s\S]{0,400}?(?:src|data-src)="(https:[^"]+)"/gi, "");
    },
    async xxxbunker(q, page, daily) {
      const extra = page > 0 ? `/${page + 1}` : "";
      const url = daily ? "https://xxxbunker.com/" : `https://xxxbunker.com/search/${enc(q)}${extra}`;
      const body = await fetchText(url);
      const items = [];
      for (const m of allMatches(/(?:src|data-src)="https:\/\/thumbs\.xxxbunker\.com\/(\d+)\.jpg"[^>]*alt="([^"]*)"/gi, body)) {
        items.push(item("XXXBunker", "xxxbunker", m[2], `https://xxxbunker.com/${m[1]}`, `https://thumbs.xxxbunker.com/${m[1]}.jpg`, "", ""));
        if (items.length >= 40) break;
      }
      return items;
    },
    async tnaflix(q, page, daily) {
      const url = daily ? "https://www.tnaflix.com/" : `https://www.tnaflix.com/search.php?what=${enc(q)}${page > 0 ? `&page=${page + 1}` : ""}`;
      return htmlPair(url, "TNAflix", "tnaflix", /href="(https:\/\/www\.tnaflix\.com\/[^"]+\/video\d+)"[\s\S]{0,800}?(?:data-src|src)="(https:\/\/(?:cdnl|img)\.tnaflix\.com\/[^"]+\.jpg)"/gi, "");
    },
    async drtuber(q, page, daily) {
      const url = daily ? "https://www.drtuber.com/" : `https://www.drtuber.com/search/videos/${enc(q)}${page > 0 ? `/${page + 1}` : ""}`;
      return htmlPair(url, "DrTuber", "drtuber", /href="(\/video\/\d+\/[^"]+)"[^>]*>\s*<img[^>]+src="(https:[^"]+)"/gi, "https://www.drtuber.com");
    },
    async pornone(q, page, daily) {
      const url = daily ? "https://www.pornone.com/" : `https://www.pornone.com/search${page > 0 ? `/${page + 1}` : ""}/?q=${enc(q)}`;
      return htmlPair(url, "PornOne", "pornone", /href="(https:\/\/(?:www\.)?pornone\.com\/[^"]+\/\d+\/)"[\s\S]{0,400}?src="(https:\/\/th-eu\d+\.pornone\.com\/[^"]+)"/gi, "");
    },
    async okxxx(q, page, daily) {
      const url = daily ? "https://ok.xxx/" : `https://ok.xxx/search/${enc(q)}/`;
      return htmlPair(url, "OK.xxx", "okxxx", /href="(\/video\/\d+\/)"[^>]*title="([^"]*)"[\s\S]{0,700}?data-original="(https:[^"]+)"/gi, "https://ok.xxx").then((rows) => rows);
    },
    async porn00(q, page, daily) {
      const url = daily ? "https://www.porn00.org/latest/" : `https://www.porn00.org/q/${enc(q)}/`;
      const body = await fetchText(url);
      const items = [];
      for (const m of allMatches(/href="(https:\/\/www.porn00.org\/video\/[^"]+)"[^>]*title="([^"]*)"[\s\S]{0,600}?data-original="(https:[^"]+)"/gi, body)) {
        items.push(item("Porn00", "porn00", m[2], m[1], m[3], "", ""));
        if (items.length >= 40) break;
      }
      return items;
    },
    async xxxfiles(q, page, daily) {
      const url = daily ? "https://www.xxxfiles.com/" : `https://www.xxxfiles.com/?s=${enc(q)}`;
      return htmlPair(url, "XXXFiles", "xxxfiles", /href="(https:\/\/www.xxxfiles.com\/videos\/\d+\/[^"]+)"[\s\S]{0,500}?src="(https:\/\/img.xxxfiles.com\/[^"]+)"/gi, "");
    },
    async xmoviesforyou(q, page, daily) {
      const url = daily ? "https://xmoviesforyou.com/" : `https://xmoviesforyou.com/?s=${enc(q)}`;
      return htmlPair(url, "XMoviesForYou", "xmoviesforyou", /href="(\/[a-z0-9-]+)"[^>]*>[\s\S]{0,500}?src="(https:\/\/xmoviescdn\.online\/[^"]+)"/gi, "https://xmoviesforyou.com");
    },
    async whoreshub(q, page, daily) {
      const url = daily ? "https://www.whoreshub.com/" : `https://www.whoreshub.com/search/${enc(q)}/`;
      const body = await fetchText(url);
      const items = [];
      const seen = new Set();
      for (const m of allMatches(/href="(https:\/\/www.whoreshub.com\/videos\/(\d+)\/[^"]+)"/gi, body)) {
        if (seen.has(m[1])) continue;
        seen.add(m[1]);
        const num = Number(m[2]);
        const bucket = Math.floor(num / 1000) * 1000;
        const title = m[1].replace(/\/+$/, "").split("/").pop().replace(/-/g, " ");
        items.push(item("WhoresHub", "whoreshub", title, m[1], `https://www.whoreshub.com/contents/videos_screenshots/${bucket}/${num}/320x180/1.jpg`, "", ""));
        if (items.length >= 40) break;
      }
      return items;
    },
    async yespornvip(q, page, daily) {
      const url = daily ? "https://yespornvip.com/" : `https://yespornvip.com/?s=${enc(q)}`;
      return htmlPair(url, "YesPornVIP", "yespornvip", /href="(https:\/\/yespornvip.com\/[a-z0-9-]+\/)"[\s\S]{0,800}?(?:data-src|src)="(https:\/\/yespornvip.com\/wp-content\/uploads\/thumbsx\/[^"]+)"/gi, "");
    },
    async justporn(q, page, daily) {
      const url = daily ? "https://www.justporn.to/" : `https://www.justporn.to/search/${enc(q)}/`;
      return htmlPair(url, "JustPorn", "justporn", /href="(https:\/\/(?:www\.)?justporn.to\/[a-z0-9-]+\/)"[\s\S]{0,700}?src="(https:\/\/justporn.to\/cover_upload\/[^"]+)"/gi, "");
    }
  };

  const ALL = Object.keys(SITES);

  window.GitVidXSearch = {
    async search({ q, source, page, tags }) {
      const query = q || "amateur";
      if (blocked(query)) return { error: "That search is blocked. GitVidX only shows legal, consensual, 18+ videos.", items: [], next: false, sources: [] };
      const daily = isDaily(query);
      const tagList = String(tags || "").split(",").map((t) => t.trim()).filter(Boolean).slice(0, 5);
      const { content, length } = splitLength(tagList);
      let send = query;
      if (!daily) {
        if (content.length) send = focused(content);
        else if (length) send = "amateur";
        else send = expand(query);
      }
      if (!send || LENGTH.has(String(send).trim().toLowerCase())) send = "amateur";
      const jobs = (!source || source === "all" || !SITES[source]) ? ALL : [source];
      const results = await Promise.all(jobs.map(async (name) => {
        try {
          const found = (await SITES[name](send, Number(page) || 0, daily)).filter(allowed);
          return { name, found };
        } catch (err) {
          return { name, found: [], error: String(err && err.message || err) };
        }
      }));
      let items = [];
      const sources = [];
      const errors = [];
      const seen = new Set();
      for (const row of results) {
        if (row.found.length) {
          sources.push(row.name);
          for (const it of row.found) {
            const key = it.page || it.id;
            if (!key || seen.has(key)) continue;
            seen.add(key);
            items.push(it);
          }
        } else if (row.error) errors.push(`${row.name}: ${row.error}`);
      }
      const fetched = items.length > 0;
      if (daily) {
        const buckets = {};
        const order = [];
        for (const it of items) {
          if (!buckets[it.source]) { buckets[it.source] = []; order.push(it.source); }
          buckets[it.source].push(it);
        }
        const mixed = [];
        let more = true;
        while (more) {
          more = false;
          for (const src of order) {
            if (buckets[src].length) { mixed.push(buckets[src].shift()); more = true; }
          }
        }
        items = mixed;
      } else {
        items = rank(items, query, content);
      }
      if (length) items = items.filter((row) => matchesLength(row, length));
      return {
        query,
        items,
        next: fetched && !daily,
        sources,
        mode: daily ? "daily" : "search",
        date: daily ? today() : null,
        error: items.length || !errors.length ? null : errors.join("; ")
      };
    }
  };
})();

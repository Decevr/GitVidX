/* Client search for GitHub Pages / home-screen PWA (no Python server). */
(function () {
  const DAILY_Q = "__daily__";
  const STOP = new Set(["a","an","the","and","or","of","to","in","for","on","with","plus","hair","sex","fuck","video","style","position","man","guy","view","camera","cam","shot","angle"]);
  const PHRASES = {
    amateur: "amateur", milf: "milf", lesbian: "lesbian", blonde: "blonde", brunette: "brunette",
    anal: "anal", pov: "pov", solo: "solo", hardcore: "hardcore", blowjob: "blowjob",
    creampie: "creampie", "big tits": "big tits", asian: "asian", latina: "latina",
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
    "fly on the wall": "fly on the wall", "third person": "third person view",
    "close up": "close up", "full body": "full body", overhead: "overhead view",
    "low angle": "low angle", "side view": "side view", "behind camera": "from behind camera",
    "face cam": "face cam", "looking at camera": "looking at camera", mirror: "mirror sex",
    handheld: "handheld camera", tripod: "tripod camera", gopro: "gopro",
    "selfie cam": "selfie", "two camera": "two camera", cinematic: "cinematic",
    "over the shoulder": "over the shoulder", "wide shot": "wide shot"
  };
  const BLOCK = /\b(child|children|kid|kids|toddler|infant|baby|babies|minor|minors|underage|under[\s-]?age|preteen|pre[\s-]?teen|loli|lolita|shota|pedo|paedo|jailbait|young[\s-]?girl|little[\s-]?girl|(1[0-7]|[0-9])\s*(yo|yr|years?\s*old)|leak|leaked|leaks|stolen|hacked|fappening|celebgate|revenge\s*porn|non[\s-]?consensual|without\s+consent|no\s+consent|hidden\s*cam|spy\s*cam|voyeur|creepshot|upskirt|downblouse|passed\s+out|unconscious|drugged|sleeping\s+nude|rape|raped|forced|blackmail|deepnude|undress)\b/i;
  const HOST_BITS = ["leak","leaked","thothub","fappening","celebgate","nudel","coomer","kemono","simpcity","fapello","cyberdrop"];

  function isDaily(q) { return String(q || "").trim().toLowerCase() === DAILY_Q; }
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
    return value;
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
        if (words.length >= 6) return words.join(" ");
      }
    }
    return words.join(" ");
  }
  function tokens(q) {
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
    const page = norm(row.page + " " + row.url);
    const list = tokens(tag);
    return list.length ? list.some((t) => tokenIn(t, title, page)) : false;
  }
  function rank(items, query, tags) {
    if (tags && tags.length) {
      const scored = items.map((row) => {
        const hits = tags.reduce((n, tag) => n + (tagMatched(row, tag) ? 1 : 0), 0);
        return { hits, row };
      }).sort((a, b) => b.hits - a.hits);
      const total = tags.length;
      const full = scored.filter((s) => s.hits >= total).map((s) => s.row);
      const almost = scored.filter((s) => s.hits >= Math.max(1, total - 1)).map((s) => s.row);
      const some = scored.filter((s) => s.hits > 0).map((s) => s.row);
      if (full.length >= 6) return full;
      if (almost.length >= 6) return almost;
      return some;
    }
    const list = tokens(query);
    const needed = Math.max(1, Math.ceil(list.length / 2));
    const scored = items.map((row) => {
      const title = norm(row.title);
      const page = norm(row.page + " " + row.url);
      const hits = list.reduce((n, t) => n + (tokenIn(t, title, page) ? 1 : 0), 0);
      return { hits, row };
    }).sort((a, b) => b.hits - a.hits);
    const strong = scored.filter((s) => s.hits >= needed).map((s) => s.row);
    return strong.length ? strong : scored.filter((s) => s.hits > 0).map((s) => s.row);
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
      let send = query;
      if (!daily) send = tagList.length ? combine(tagList) : expand(query);
      if (!send) send = "amateur";
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
        items = rank(items, query, tagList);
      }
      return {
        query,
        items,
        next: items.length > 0 && !daily,
        sources,
        mode: daily ? "daily" : "search",
        date: daily ? today() : null,
        error: items.length || !errors.length ? null : errors.join("; ")
      };
    }
  };
})();

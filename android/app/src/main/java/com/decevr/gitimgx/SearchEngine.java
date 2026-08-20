package com.decevr.gitimgx;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class SearchEngine {
    private static final String BROWSER_UA =
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36";
    private static final String DESKTOP_UA =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
    private static final Pattern BLOCK = Pattern.compile(
            "\\b("
                    + "child|children|kid|kids|toddler|infant|baby|babies|minor|minors|"
                    + "underage|under[\\s-]?age|preteen|pre[\\s-]?teen|loli|lolita|shota|"
                    + "pedo|paedo|jailbait|young[\\s-]?girl|little[\\s-]?girl|"
                    + "(1[0-7]|[0-9])\\s*(yo|yr|years?\\s*old)|"
                    + "leak|leaked|leaks|stolen|hacked|fappening|celebgate|"
                    + "revenge\\s*porn|non[\\s-]?consensual|without\\s+consent|no\\s+consent|"
                    + "hidden\\s*cam|spy\\s*cam|voyeur|creepshot|upskirt|downblouse|"
                    + "passed\\s+out|unconscious|drugged|sleeping\\s+nude|"
                    + "rape|raped|forced|blackmail|deepnude|undress"
                    + ")\\b",
            Pattern.CASE_INSENSITIVE
    );
    private static final String[] BLOCKED_HOST_BITS = {
            "leak", "leaked", "thothub", "fappening", "celebgate", "nudel",
            "coomer", "kemono", "simpcity", "fapello", "cyberdrop"
    };
    static final String BLOCK_REASON =
            "That search is blocked. GitVidX only shows legal, consensual, 18+ videos. "
                    + "No leaks, hidden cameras, or non-consensual content.";
    static final String DAILY_Q = "__daily__";
    private static final Set<String> WEAK_SOLO = new HashSet<>(Arrays.asList(
            "black", "dark", "red", "pink", "blue", "purple", "grey", "gray", "silver",
            "large", "small", "medium", "big", "huge", "tiny", "little", "round", "full",
            "close", "wide", "low", "side", "third", "two", "over", "looking", "from",
            "behind", "against", "natural", "perky", "fake",
            "tits", "tit", "boobs", "boob", "ass", "butt", "booty", "breasts", "breast"
    ));
    private static final Set<String> PHRASE_ONLY = new HashSet<>(Arrays.asList(
            "amazon", "butterfly", "black hair", "pink hair", "blue hair", "purple hair",
            "looking at camera", "over the shoulder", "fly on the wall", "third person",
            "behind camera", "delivery guy", "maintenance man", "tramp stamp", "tan line",
            "anvil", "lotus"
    ));

    String blockedQuery(String query) {
        if (query != null && BLOCK.matcher(query).find()) {
            return BLOCK_REASON;
        }
        return null;
    }

    JSONObject search(String query, String source, int page) throws Exception {
        return search(query, source, page, false);
    }

    JSONObject search(String query, String source, int page, boolean refresh) throws Exception {
        return search(query, source, page, refresh, null);
    }

    JSONObject search(String query, String source, int page, boolean refresh, String tagsRaw) throws Exception {
        if (query == null || query.trim().isEmpty()) {
            query = "amateur";
        }
        if (isDaily(query) && !refresh) {
            JSONObject cached = loadDaily(source, page);
            if (cached != null) return cached;
        }
        final String q = query;
        final List<String> tags = parseTags(tagsRaw);
        final String send;
        if (isDaily(query)) {
            send = query;
        } else if (!tags.isEmpty()) {
            send = focusedSearchQuery(tags);
        } else {
            send = expandSearchQuery(query);
        }
        final int p = page;
        List<NamedSearch> jobs = new ArrayList<>();
        if ("all".equals(source) || source == null || source.isEmpty()) {
            jobs.add(new NamedSearch("pornhub", this::pornhub));
            jobs.add(new NamedSearch("xvideos", this::xvideos));
            jobs.add(new NamedSearch("xhamster", this::xhamster));
            jobs.add(new NamedSearch("xnxx", this::xnxx));
            jobs.add(new NamedSearch("redtube", this::redtube));
            jobs.add(new NamedSearch("eporner", this::eporner));
            jobs.add(new NamedSearch("xxxbunker", this::xxxbunker));
            jobs.add(new NamedSearch("tnaflix", this::tnaflix));
            jobs.add(new NamedSearch("drtuber", this::drtuber));
            jobs.add(new NamedSearch("pornone", this::pornone));
            jobs.add(new NamedSearch("okxxx", this::okxxx));
            jobs.add(new NamedSearch("porn00", this::porn00));
            jobs.add(new NamedSearch("xxxfiles", this::xxxfiles));
            jobs.add(new NamedSearch("xmoviesforyou", this::xmoviesforyou));
            jobs.add(new NamedSearch("whoreshub", this::whoreshub));
            jobs.add(new NamedSearch("yespornvip", this::yespornvip));
            jobs.add(new NamedSearch("justporn", this::justporn));
        } else {
            jobs.add(new NamedSearch(source, pick(source)));
        }

        List<JSONObject> items = new ArrayList<>();
        JSONArray sources = new JSONArray();
        List<String> errors = new ArrayList<>();
        java.util.concurrent.ExecutorService pool = java.util.concurrent.Executors.newFixedThreadPool(Math.min(8, Math.max(1, jobs.size())));
        try {
            List<java.util.concurrent.Future<NamedResult>> futures = new ArrayList<>();
            for (NamedSearch job : jobs) {
                futures.add(pool.submit(() -> {
                    List<JSONObject> found = new ArrayList<>();
                    for (JSONObject row : job.fn.run(send, p)) {
                        if (allowedItem(row)) found.add(row);
                    }
                    return new NamedResult(job.name, found, null);
                }));
            }
            for (int i = 0; i < futures.size(); i++) {
                try {
                    NamedResult result = futures.get(i).get();
                    if (!result.items.isEmpty()) {
                        items.addAll(result.items);
                        sources.put(result.name);
                    }
                } catch (Exception error) {
                    errors.add(jobs.get(i).name + ": " + error.getMessage());
                }
            }
        } finally {
            pool.shutdownNow();
        }

        Map<String, JSONObject> unique = new LinkedHashMap<>();
        for (JSONObject row : items) {
            String key = row.optString("page", row.optString("id"));
            if (!key.isEmpty() && !unique.containsKey(key)) {
                unique.put(key, row);
            }
        }
        List<JSONObject> ordered = new ArrayList<>(unique.values());
        if (isDaily(q)) {
            ordered = interleave(ordered);
        } else {
            ordered = rankItems(ordered, q, tags);
        }
        JSONArray out = new JSONArray();
        for (JSONObject row : ordered) {
            out.put(row);
        }
        JSONObject payload = new JSONObject();
        payload.put("query", q);
        payload.put("items", out);
        payload.put("next", out.length() > 0 && !isDaily(q));
        payload.put("sources", sources);
        payload.put("mode", isDaily(q) ? "daily" : "search");
        if (isDaily(q)) {
            payload.put("date", todayStamp());
        } else {
            payload.put("date", JSONObject.NULL);
        }
        if (out.length() == 0 && !errors.isEmpty()) {
            payload.put("error", String.join("; ", errors));
        } else {
            payload.put("error", JSONObject.NULL);
        }
        if (isDaily(q) && out.length() > 0) {
            saveDaily(source, page, payload);
        }
        return payload;
    }

    ImageResult fetchImage(String target) throws Exception {
        return fetchImage(target, null);
    }

    ImageResult fetchImage(String target, String referer) throws Exception {
        target = cleanThumb(target);
        URL parsed = new URL(target);
        if (!"https".equalsIgnoreCase(parsed.getProtocol()) || !isPublicHost(parsed.getHost())) {
            throw new IllegalArgumentException("Blocked image url");
        }
        String ref = referer;
        if (ref == null || ref.isEmpty()) {
            String host = parsed.getHost().toLowerCase(Locale.US);
            if (host.contains("xvideos")) ref = "https://www.xvideos.com/";
            else if (host.contains("xnxx")) ref = "https://www.xnxx.com/";
            else if (host.contains("xhamster")) ref = "https://xhamster.com/";
            else if (host.contains("rdtcdn") || host.contains("phncdn") || host.contains("redtube"))
                ref = "https://www.redtube.com/";
        }
        HttpURLConnection connection = open(parsed, "image/avif,image/webp,image/*,*/*;q=0.8", ref);
        try {
            int code = connection.getResponseCode();
            if (code >= 400) {
                throw new IllegalStateException("Image fetch failed");
            }
            String type = connection.getContentType();
            if (type == null) {
                type = "application/octet-stream";
            }
            if (!type.contains("image") && !type.contains("octet-stream")) {
                throw new IllegalStateException("Not an image");
            }
            return new ImageResult(type.split(";")[0].trim(), readLimited(connection.getInputStream(), 8_000_000));
        } finally {
            connection.disconnect();
        }
    }

    private boolean isDaily(String query) {
        return query != null && DAILY_Q.equalsIgnoreCase(query.trim());
    }

    private String canonQuery(String query) {
        String raw = query == null ? "" : query.trim().toLowerCase(Locale.US);
        String dashed = raw.replaceAll("[\\s_]+", "-");
        if (dashed.equals("step-sis") || dashed.equals("stepsis") || dashed.equals("step-sister")
                || dashed.equals("stepsister")) {
            return "step-sis";
        }
        if (dashed.equals("only-fans") || dashed.equals("onlyfans")) return "onlyfans";
        if (dashed.equals("ai") || dashed.equals("ai-generated")) return "ai";
        if (dashed.equals("home-made") || dashed.equals("homemade")) return "homemade";
        if (dashed.equals("teen") || dashed.equals("18-teen") || dashed.equals("18+-teen")) return "teen";
        if (dashed.equals("big-tits") || raw.equals("big tits")) return "big tits";
        if (dashed.equals("tan-line") || dashed.equals("tanlines") || raw.equals("tan line")) return "tan line";
        if (dashed.equals("small-tits") || dashed.equals("tiny-tits") || dashed.equals("tiny-boobs")
                || dashed.equals("small-boobs") || dashed.equals("little-tits") || dashed.equals("flat-chest")
                || raw.equals("small tits")) return "small tits";
        if (dashed.equals("medium-tits") || dashed.equals("medium-boobs") || raw.equals("medium tits")) return "medium tits";
        if (dashed.equals("large-tits") || dashed.equals("huge-tits") || dashed.equals("giant-tits")
                || dashed.equals("massive-tits") || dashed.equals("huge-boobs") || dashed.equals("busty")
                || raw.equals("large tits")) return "large tits";
        if (dashed.equals("big-boobs") || raw.equals("big boobs")) return "big tits";
        if (dashed.equals("natural-tits") || raw.equals("natural tits")) return "natural tits";
        if (dashed.equals("perky-tits") || raw.equals("perky tits")) return "perky tits";
        if (dashed.equals("large-ass") || dashed.equals("big-ass") || raw.equals("large ass")) return "large ass";
        if (dashed.equals("round-ass") || raw.equals("round ass")) return "round ass";
        if (dashed.equals("lap-dance") || dashed.equals("lapdance") || raw.equals("lap dance")) return "lap dance";
        if (dashed.equals("strip-tease") || dashed.equals("striptease")) return "striptease";
        if (dashed.equals("story-line") || dashed.equals("storyline")) return "storyline";
        if (dashed.equals("full-movie") || raw.equals("full movie")) return "full movie";
        if (dashed.equals("full-scene") || raw.equals("full scene")) return "full scene";
        if (dashed.equals("doggy") || dashed.equals("doggystyle") || dashed.equals("doggy-style")) return "doggy";
        if (dashed.equals("reverse-cowgirl") || dashed.equals("reversecowgirl") || raw.equals("reverse cowgirl")) return "reverse cowgirl";
        if (dashed.equals("prone-bone") || dashed.equals("pronebone") || raw.equals("prone bone")) return "prone bone";
        if (dashed.equals("mating-press") || raw.equals("mating press")) return "mating press";
        if (dashed.equals("face-sitting") || dashed.equals("facesitting")) return "facesitting";
        if (dashed.equals("legs-up") || raw.equals("legs up")) return "legs up";
        if (dashed.equals("bent-over") || raw.equals("bent over")) return "bent over";
        if (dashed.equals("full-nelson") || raw.equals("full nelson")) return "full nelson";
        if (dashed.equals("against-wall") || dashed.equals("against-the-wall") || raw.equals("against wall")) return "against wall";
        if (dashed.equals("sixty-nine") || dashed.equals("69")) return "69";
        if (dashed.equals("redhead") || dashed.equals("red-hair")) return "redhead";
        if (dashed.equals("black-hair") || raw.equals("black hair")) return "black hair";
        if (dashed.equals("pink-hair") || raw.equals("pink hair")) return "pink hair";
        if (dashed.equals("blue-hair") || raw.equals("blue hair")) return "blue hair";
        if (dashed.equals("purple-hair") || raw.equals("purple hair")) return "purple hair";
        if (dashed.equals("grey-hair") || dashed.equals("gray") || dashed.equals("gray-hair")) return "grey";
        if (dashed.equals("phone-video") || dashed.equals("cellphone")) return "cellphone";
        if (dashed.equals("hotel-sex") || dashed.equals("hotel")) return "hotel";
        if (dashed.equals("motel-sex") || dashed.equals("motel")) return "motel";
        if (dashed.equals("car-sex") || dashed.equals("car")) return "car";
        if (dashed.equals("public-sex") || dashed.equals("public")) return "public";
        if (dashed.equals("sneaky-sex") || dashed.equals("sneaky")) return "sneaky";
        if (dashed.equals("tramp-stamp") || raw.equals("tramp stamp")) return "tramp stamp";
        if (dashed.equals("delivery-guy") || raw.equals("delivery guy")) return "delivery guy";
        if (dashed.equals("maintenance-man") || dashed.equals("maintaince-man") || raw.equals("maintenance man")) return "maintenance man";
        if (dashed.equals("fly-on-the-wall") || raw.equals("fly on the wall")) return "fly on the wall";
        if (dashed.equals("third-person") || raw.equals("third person")) return "third person";
        if (dashed.equals("close-up") || dashed.equals("closeup") || raw.equals("close up")) return "close up";
        if (dashed.equals("full-body") || raw.equals("full body")) return "full body";
        if (dashed.equals("low-angle") || raw.equals("low angle")) return "low angle";
        if (dashed.equals("side-view") || raw.equals("side view")) return "side view";
        if (dashed.equals("behind-camera") || raw.equals("behind camera")) return "behind camera";
        if (dashed.equals("face-cam") || raw.equals("face cam")) return "face cam";
        if (dashed.equals("looking-at-camera") || raw.equals("looking at camera")) return "looking at camera";
        if (dashed.equals("selfie-cam") || raw.equals("selfie cam")) return "selfie cam";
        if (dashed.equals("two-camera") || raw.equals("two camera")) return "two camera";
        if (dashed.equals("over-the-shoulder") || raw.equals("over the shoulder")) return "over the shoulder";
        if (dashed.equals("wide-shot") || dashed.equals("wide-angle") || raw.equals("wide shot")) return "wide shot";
        if (dashed.equals("michigan") || dashed.equals("michigan-position")) return "michigan";
        if (dashed.equals("slipped-in") || dashed.equals("slipped-it-in")
                || dashed.equals("accidentally-slipped-it-in") || dashed.equals("accidentally-slipped-in")
                || raw.equals("slipped in")) return "slipped in";
        return raw;
    }

    private String expandSearchQuery(String query) {
        switch (canonQuery(query)) {
            case "step-sis": return "stepsister";
            case "onlyfans": return "onlyfans";
            case "ai": return "ai generated";
            case "homemade": return "homemade";
            case "teen": return "teen";
            case "cheating": return "cheating wife";
            case "big tits": return "big tits";
            case "tan line": return "tan lines";
            case "small tits": return "small tits";
            case "medium tits": return "medium tits";
            case "large tits": return "huge tits";
            case "natural tits": return "natural tits";
            case "perky tits": return "perky tits";
            case "large ass": return "big ass";
            case "round ass": return "round ass";
            case "petite": return "petite";
            case "curvy": return "curvy";
            case "thick": return "thick";
            case "pawg": return "pawg";
            case "cmnf": return "cmnf";
            case "cfnm": return "cfnm";
            case "lap dance": return "lap dance";
            case "striptease": return "striptease";
            case "oil": return "oiled";
            case "massage": return "massage";
            case "storyline": return "storyline";
            case "full movie": return "full movie";
            case "full scene": return "full scene";
            case "cuckold": return "cuckold";
            case "missionary": return "missionary";
            case "doggy": return "doggy style";
            case "cowgirl": return "cowgirl";
            case "reverse cowgirl": return "reverse cowgirl";
            case "spooning": return "spooning";
            case "standing": return "standing sex";
            case "69": return "69";
            case "prone bone": return "prone bone";
            case "mating press": return "mating press";
            case "lotus": return "lotus position";
            case "piledriver": return "piledriver";
            case "butterfly": return "butterfly position";
            case "amazon": return "amazon position";
            case "wheelbarrow": return "wheelbarrow";
            case "anvil": return "anvil position";
            case "facesitting": return "facesitting";
            case "scissoring": return "scissoring";
            case "sideways": return "sideways fuck";
            case "legs up": return "legs up";
            case "bent over": return "bent over";
            case "full nelson": return "full nelson";
            case "against wall": return "against the wall";
            case "chair": return "chair sex";
            case "michigan": return "michigan";
            case "slipped in": return "slipped it in";
            case "redhead": return "redhead";
            case "black hair": return "black hair";
            case "auburn": return "auburn";
            case "platinum": return "platinum blonde";
            case "grey": return "grey hair";
            case "pink hair": return "pink hair";
            case "blue hair": return "blue hair";
            case "purple hair": return "purple hair";
            case "cellphone": return "cellphone video";
            case "snapchat": return "snapchat";
            case "hotel": return "hotel sex";
            case "motel": return "motel sex";
            case "car": return "car sex";
            case "public": return "public sex";
            case "sneaky": return "sneaky sex";
            case "quickie": return "quickie";
            case "tramp stamp": return "tramp stamp";
            case "delivery guy": return "delivery guy";
            case "maintenance man": return "maintenance man";
            case "fly on the wall": return "fly on the wall";
            case "third person": return "third person view";
            case "close up": return "close up";
            case "full body": return "full body";
            case "overhead": return "overhead view";
            case "low angle": return "low angle";
            case "side view": return "side view";
            case "behind camera": return "from behind camera";
            case "face cam": return "face cam";
            case "looking at camera": return "looking at camera";
            case "mirror": return "mirror sex";
            case "handheld": return "handheld camera";
            case "tripod": return "tripod camera";
            case "gopro": return "gopro";
            case "selfie cam": return "selfie";
            case "two camera": return "two camera";
            case "cinematic": return "cinematic";
            case "over the shoulder": return "over the shoulder";
            case "wide shot": return "wide shot";
            default: return query == null ? "" : query.trim();
        }
    }

    private List<String> categoryPhrases(String key) {
        switch (key) {
            case "step-sis":
                return java.util.Arrays.asList("stepsister", "step sister", "step-sister", "stepsis", "step sis", "step-sis");
            case "homemade":
                return java.util.Arrays.asList("homemade", "home made", "homemade amateur");
            case "onlyfans":
                return java.util.Arrays.asList("onlyfans", "only fans", "only-fans");
            case "ai":
                return java.util.Arrays.asList("ai generated", "ai porn", "ai generated porn");
            case "teen":
                return java.util.Arrays.asList("teen", "18 teen");
            case "amateur": return java.util.Arrays.asList("amateur");
            case "milf": return java.util.Arrays.asList("milf");
            case "lesbian": return java.util.Arrays.asList("lesbian");
            case "blonde": return java.util.Arrays.asList("blonde", "blond");
            case "brunette": return java.util.Arrays.asList("brunette");
            case "anal": return java.util.Arrays.asList("anal");
            case "pov": return java.util.Arrays.asList("pov");
            case "solo": return java.util.Arrays.asList("solo", "masturbation");
            case "hardcore": return java.util.Arrays.asList("hardcore");
            case "blowjob": return java.util.Arrays.asList("blowjob", "blow job", "bj");
            case "creampie": return java.util.Arrays.asList("creampie", "cream pie");
            case "tan line": return java.util.Arrays.asList("tan line", "tanline", "tan lines", "tanlines");
            case "small tits": return Arrays.asList("small tits", "small tit", "tiny tits", "tiny tit", "little tits", "small boobs", "tiny boobs", "little boobs", "small breasts", "tiny breasts", "flat chest", "small chest", "petite tits", "a cup");
            case "medium tits": return Arrays.asList("medium tits", "medium boobs", "medium breasts", "average tits", "c cup", "medium sized tits");
            case "large tits": return Arrays.asList("large tits", "huge tits", "big tits", "giant tits", "massive tits", "big boobs", "huge boobs", "massive boobs", "giant boobs", "big breasts", "huge breasts", "large breasts", "big naturals", "busty", "bigtits");
            case "big tits": return Arrays.asList("big tits", "bigtits", "big boobs", "huge tits", "huge boobs", "big breasts");
            case "natural tits": return Arrays.asList("natural tits", "natural breasts", "natural boobs", "naturals", "real tits");
            case "perky tits": return Arrays.asList("perky tits", "perky breasts", "perky boobs");
            case "large ass": return Arrays.asList("large ass", "big ass", "huge ass", "fat ass", "phat ass", "big booty", "huge booty", "bubble butt", "big butt");
            case "round ass": return Arrays.asList("round ass", "round booty", "peach ass", "bubble butt");
            case "petite": return java.util.Arrays.asList("petite");
            case "curvy": return java.util.Arrays.asList("curvy");
            case "thick": return java.util.Arrays.asList("thick");
            case "pawg": return java.util.Arrays.asList("pawg");
            case "cmnf": return java.util.Arrays.asList("cmnf", "clothed male naked female");
            case "cfnm": return java.util.Arrays.asList("cfnm", "clothed female naked male");
            case "lap dance": return java.util.Arrays.asList("lap dance", "lapdance");
            case "striptease": return java.util.Arrays.asList("striptease", "strip tease");
            case "oil": return java.util.Arrays.asList("oiled", "oil massage");
            case "massage": return java.util.Arrays.asList("massage");
            case "storyline": return java.util.Arrays.asList("storyline", "story line");
            case "full movie": return java.util.Arrays.asList("full movie", "full length");
            case "full scene": return java.util.Arrays.asList("full scene");
            case "asian": return java.util.Arrays.asList("asian");
            case "latina": return java.util.Arrays.asList("latina", "latin");
            case "threesome": return java.util.Arrays.asList("threesome");
            case "feet": return java.util.Arrays.asList("feet", "foot fetish", "footjob");
            case "socks": return java.util.Arrays.asList("socks", "sock", "sockjob", "sock fetish");
            case "cheating": return java.util.Arrays.asList("cheating", "cheating wife");
            case "cuckold": return java.util.Arrays.asList("cuckold", "cuckolding");
            case "missionary": return java.util.Arrays.asList("missionary");
            case "doggy": return java.util.Arrays.asList("doggy", "doggy style", "doggystyle", "from behind");
            case "cowgirl": return Arrays.asList("cowgirl", "cow girl");
            case "reverse cowgirl": return Arrays.asList("reverse cowgirl", "reversecowgirl");
            case "spooning": return java.util.Arrays.asList("spooning", "spoon");
            case "standing": return java.util.Arrays.asList("standing", "standing sex", "standing fuck");
            case "69": return java.util.Arrays.asList("69", "sixty nine");
            case "prone bone": return java.util.Arrays.asList("prone bone", "pronebone");
            case "mating press": return java.util.Arrays.asList("mating press", "matingpress");
            case "lotus": return Arrays.asList("lotus position", "lotus pose");
            case "piledriver": return Arrays.asList("piledriver", "pile driver");
            case "butterfly": return Arrays.asList("butterfly position", "butterfly pose");
            case "amazon": return Arrays.asList("amazon position", "amazon pose");
            case "wheelbarrow": return java.util.Arrays.asList("wheelbarrow");
            case "anvil": return java.util.Arrays.asList("anvil", "anvil position");
            case "facesitting": return java.util.Arrays.asList("facesitting", "face sitting", "queening");
            case "scissoring": return java.util.Arrays.asList("scissoring", "scissor");
            case "sideways": return java.util.Arrays.asList("sideways", "side fuck", "on the side");
            case "legs up": return java.util.Arrays.asList("legs up", "legs in the air");
            case "bent over": return java.util.Arrays.asList("bent over", "bend over");
            case "full nelson": return java.util.Arrays.asList("full nelson");
            case "against wall": return java.util.Arrays.asList("against the wall", "wall sex", "pinned to the wall");
            case "chair": return java.util.Arrays.asList("chair sex", "chair fuck");
            case "michigan": return java.util.Arrays.asList("michigan", "michigan sex");
            case "slipped in": return java.util.Arrays.asList("slipped it in", "accidentally slipped it in", "accidentally slipped in", "accidental slip");
            case "redhead": return Arrays.asList("redhead", "red hair", "red haired", "ginger");
            case "black hair": return Arrays.asList("black hair", "black haired", "dark hair", "jet black hair");
            case "auburn": return java.util.Arrays.asList("auburn");
            case "platinum": return java.util.Arrays.asList("platinum blonde", "platinum");
            case "grey": return java.util.Arrays.asList("grey hair", "gray hair", "silver hair");
            case "pink hair": return java.util.Arrays.asList("pink hair");
            case "blue hair": return java.util.Arrays.asList("blue hair");
            case "purple hair": return java.util.Arrays.asList("purple hair");
            case "cellphone": return java.util.Arrays.asList("cellphone", "phone video", "mobile video");
            case "snapchat": return java.util.Arrays.asList("snapchat");
            case "hotel": return Arrays.asList("hotel sex", "hotel room", "hotel fuck");
            case "motel": return Arrays.asList("motel sex", "motel room", "motel fuck");
            case "car": return Arrays.asList("car sex", "car fuck", "in the car", "backseat", "back seat");
            case "public": return Arrays.asList("public sex", "public fuck", "in public");
            case "sneaky": return Arrays.asList("sneaky sex", "sneaky fuck", "sneaky");
            case "quickie": return java.util.Arrays.asList("quickie");
            case "tramp stamp": return java.util.Arrays.asList("tramp stamp");
            case "delivery guy": return java.util.Arrays.asList("delivery guy", "delivery man");
            case "maintenance man": return java.util.Arrays.asList("maintenance man", "handyman");
            case "fly on the wall": return java.util.Arrays.asList("fly on the wall", "fly-on-the-wall", "third person camera");
            case "third person": return java.util.Arrays.asList("third person", "third person view");
            case "close up": return java.util.Arrays.asList("close up", "close-up", "closeup");
            case "full body": return java.util.Arrays.asList("full body", "fullbody");
            case "overhead": return java.util.Arrays.asList("overhead view", "top down", "birds eye");
            case "low angle": return java.util.Arrays.asList("low angle");
            case "side view": return java.util.Arrays.asList("side view", "side angle");
            case "behind camera": return java.util.Arrays.asList("camera from behind", "shot from behind");
            case "face cam": return java.util.Arrays.asList("face cam", "facecam");
            case "looking at camera": return java.util.Arrays.asList("looking at camera", "looks at camera");
            case "mirror": return java.util.Arrays.asList("mirror fuck", "mirror sex");
            case "handheld": return java.util.Arrays.asList("handheld camera", "handheld");
            case "tripod": return java.util.Arrays.asList("tripod");
            case "gopro": return java.util.Arrays.asList("gopro");
            case "selfie cam": return java.util.Arrays.asList("selfie", "front camera");
            case "two camera": return java.util.Arrays.asList("two camera", "dual camera", "multi cam");
            case "cinematic": return java.util.Arrays.asList("cinematic");
            case "over the shoulder": return java.util.Arrays.asList("over the shoulder");
            case "wide shot": return java.util.Arrays.asList("wide shot", "wide angle");
            default: return new ArrayList<>();
        }
    }

    private List<String> rankingTerms(String query) {
        String key = canonQuery(query);
        LinkedHashSet<String> terms = new LinkedHashSet<>();
        List<String> phrases = new ArrayList<>(categoryPhrases(key));
        if (query != null && !query.trim().isEmpty()) phrases.add(query.trim().toLowerCase(Locale.US));
        String expanded = expandSearchQuery(query);
        if (expanded != null && !expanded.isEmpty()) phrases.add(expanded.toLowerCase(Locale.US));
        for (String phrase : phrases) {
            String norm = phrase.replaceAll("[^a-z0-9]+", " ").trim();
            if (norm.isEmpty()) continue;
            terms.add(norm);
            for (String token : norm.split("\\s+")) {
                if (token.equals("a") || token.equals("an") || token.equals("the") || token.equals("and")
                        || token.equals("or") || token.equals("of") || token.equals("to") || token.equals("in")
                        || token.equals("for") || token.equals("on") || token.equals("with") || token.equals("plus")
                        || token.equals("hair") || token.equals("sex") || token.equals("fuck") || token.equals("video")
                        || token.equals("style") || token.equals("position") || token.equals("man") || token.equals("guy")
                        || token.equals("view") || token.equals("camera") || token.equals("cam")
                        || token.equals("shot") || token.equals("angle")) {
                    continue;
                }
                if (token.length() >= 2 || token.equals("ai")) terms.add(token);
            }
            String compact = phrase.replaceAll("[^a-z0-9]+", "");
            if (compact.length() >= 3) terms.add(compact);
        }
        return new ArrayList<>(terms);
    }

    private int relevanceScore(JSONObject item, List<String> terms) {
        String title = item.optString("title").toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
        String page = (item.optString("page") + " " + item.optString("url"))
                .toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
        String compact = title.replace(" ", "");
        if (terms.isEmpty()) return 1;
        int score = 0;
        for (String term : terms) {
            if (term.contains(" ")) {
                if (title.contains(term)) score += 12;
                else if (page.contains(term)) score += 4;
                continue;
            }
            if ("ai".equals(term)) {
                if (Pattern.compile("\\bai\\b").matcher(title).find()) score += 10;
                else if (Pattern.compile("\\bai\\b").matcher(page).find()) score += 3;
                continue;
            }
            Pattern word = Pattern.compile("\\b" + Pattern.quote(term) + "\\b");
            if (word.matcher(title).find()) score += 6;
            else if (term.length() >= 4 && compact.contains(term)) score += 5;
            else if (word.matcher(page).find()) score += 2;
        }
        return score;
    }

    private boolean isStop(String token) {
        return token.equals("a") || token.equals("an") || token.equals("the") || token.equals("and")
                || token.equals("or") || token.equals("of") || token.equals("to") || token.equals("in")
                || token.equals("for") || token.equals("on") || token.equals("with") || token.equals("plus")
                || token.equals("hair") || token.equals("sex") || token.equals("fuck") || token.equals("video")
                || token.equals("style") || token.equals("position") || token.equals("man") || token.equals("guy")
                || token.equals("view") || token.equals("camera") || token.equals("cam")
                || token.equals("shot") || token.equals("angle");
    }

    private String combineSearchQuery(List<String> tags) {
        LinkedHashSet<String> words = new LinkedHashSet<>();
        for (String tag : tags) {
            for (String word : expandSearchQuery(tag).split("\\s+")) {
                String key = word.toLowerCase(Locale.US);
                if (key.isEmpty() || isStop(key)) continue;
                words.add(word);
                if (words.size() >= 5) return String.join(" ", words);
            }
        }
        return String.join(" ", words);
    }

    private int focusScore(String tag) {
        int score = distinctiveTokens(tag).stream().mapToInt(String::length).sum();
        if (expandSearchQuery(tag).contains(" ")) score += 4;
        String key = canonQuery(tag);
        if (key.equals("cellphone") || key.equals("snapchat") || key.equals("homemade") || key.equals("amateur")
                || key.equals("onlyfans") || key.equals("ai") || key.equals("pov")
                || key.equals("fly on the wall") || key.equals("third person") || key.equals("close up")
                || key.equals("full body") || key.equals("overhead") || key.equals("low angle")
                || key.equals("side view") || key.equals("behind camera") || key.equals("face cam")
                || key.equals("looking at camera") || key.equals("mirror") || key.equals("handheld")
                || key.equals("tripod") || key.equals("gopro") || key.equals("selfie cam")
                || key.equals("two camera") || key.equals("cinematic") || key.equals("over the shoulder")
                || key.equals("wide shot")) {
            score -= 8;
        }
        return score;
    }

    private String focusedSearchQuery(List<String> tags) {
        List<String> ranked = new ArrayList<>(tags);
        ranked.sort((a, b) -> Integer.compare(focusScore(b), focusScore(a)));
        LinkedHashSet<String> phrases = new LinkedHashSet<>();
        for (int i = 0; i < ranked.size() && phrases.size() < 2; i++) {
            String phrase = expandSearchQuery(ranked.get(i));
            if (phrase != null && !phrase.trim().isEmpty()) phrases.add(phrase);
        }
        if (!phrases.isEmpty()) return String.join(" ", phrases);
        return combineSearchQuery(ranked.subList(0, Math.min(3, ranked.size())));
    }

    private boolean tokensNear(String title, List<String> toks) {
        if (toks.size() <= 1) return true;
        List<Integer> starts = new ArrayList<>();
        for (String tok : toks) {
            Matcher match = Pattern.compile("\\b" + Pattern.quote(tok) + "\\b").matcher(title);
            if (!match.find()) return true;
            starts.add(match.start());
        }
        int min = starts.get(0);
        int max = starts.get(0);
        int extra = 0;
        for (int i = 0; i < starts.size(); i++) {
            min = Math.min(min, starts.get(i));
            max = Math.max(max, starts.get(i));
            extra += toks.get(i).length();
        }
        return max - min <= 28 + extra;
    }

    private boolean aliasHitsTitle(String title, String compact, String alias) {
        String phrase = alias.toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
        if (phrase.isEmpty()) return false;
        if (!phrase.contains(" ")) {
            if (Pattern.compile("\\b" + Pattern.quote(phrase) + "\\b").matcher(title).find()) return true;
        } else if (title.contains(phrase)) return true;
        String glued = phrase.replace(" ", "");
        if (glued.length() >= 5 && compact.contains(glued)) return true;
        List<String> words = new ArrayList<>();
        List<String> toks = new ArrayList<>();
        for (String tok : phrase.split("\\s+")) {
            if (tok.isEmpty()) continue;
            words.add(tok);
            if (isStop(tok)) continue;
            if (tok.length() >= 2 || tok.equals("ai")) toks.add(tok);
        }
        if (toks.isEmpty()) return false;
        if (words.size() > 1 && toks.size() == 1) return false;
        boolean onlyWeak = true;
        for (String tok : toks) {
            if (!WEAK_SOLO.contains(tok) && tok.length() >= 4) onlyWeak = false;
        }
        if (onlyWeak) return false;
        for (String tok : toks) {
            if (!tokenInItem(tok, title, "", compact)) return false;
        }
        return tokensNear(title, toks);
    }

    private List<String> distinctiveTokens(String query) {
        LinkedHashSet<String> tokens = new LinkedHashSet<>();
        String key = canonQuery(query).replaceAll("[^a-z0-9]+", " ").trim();
        for (String token : key.split("\\s+")) {
            if (token.isEmpty() || isStop(token)) continue;
            if (token.length() >= 2 || token.equals("ai")) tokens.add(token);
        }
        if (!tokens.isEmpty()) return new ArrayList<>(tokens);
        for (String token : expandSearchQuery(query).toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim().split("\\s+")) {
            if (token.isEmpty() || isStop(token)) continue;
            if (token.length() >= 2 || token.equals("ai")) tokens.add(token);
        }
        return new ArrayList<>(tokens);
    }

    private boolean tokenInItem(String token, String title, String page, String compact) {
        if ("ai".equals(token)) {
            return Pattern.compile("\\bai\\b").matcher(title).find() || Pattern.compile("\\bai\\b").matcher(page).find();
        }
        Pattern word = Pattern.compile("\\b" + Pattern.quote(token) + "\\b");
        if (word.matcher(title).find()) return true;
        if (token.length() >= 4 && compact.contains(token)) return true;
        return word.matcher(page).find();
    }

    private List<String> negateFor(String key) {
        switch (key) {
            case "small tits":
                return Arrays.asList("huge tits", "massive tits", "enormous tits", "giant tits", "big tits", "large tits", "huge boobs", "massive boobs", "big boobs");
            case "large tits":
            case "big tits":
                return Arrays.asList("small tits", "tiny tits", "flat chest", "little tits", "small boobs", "tiny boobs");
            case "medium tits":
                return Arrays.asList("huge tits", "massive tits", "giant tits", "tiny tits", "flat chest");
            case "large ass":
                return Arrays.asList("flat ass", "no ass", "skinny ass");
            case "round ass":
                return Arrays.asList("flat ass");
            case "petite":
                return Arrays.asList("bbw", "ssbbw", "plus size");
            case "natural tits":
                return Arrays.asList("fake tits", "fake boobs", "implants", "fake breasts");
            case "blonde":
                return Arrays.asList("brunette", "redhead", "ginger", "black hair", "brown hair");
            case "brunette":
                return Arrays.asList("blonde", "blond", "redhead", "ginger", "platinum");
            case "redhead":
                return Arrays.asList("blonde", "blond", "brunette", "black hair", "platinum");
            case "black hair":
                return Arrays.asList("blonde", "blond", "redhead", "ginger", "platinum");
            case "platinum":
                return Arrays.asList("brunette", "redhead", "ginger", "black hair", "brown hair");
            default:
                return new ArrayList<>();
        }
    }

    private List<String> tagAliasList(String tag) {
        String key = canonQuery(tag);
        LinkedHashSet<String> aliases = new LinkedHashSet<>(categoryPhrases(key));
        if (!PHRASE_ONLY.contains(key)) aliases.add(key);
        aliases.add(expandSearchQuery(tag));
        return new ArrayList<>(aliases);
    }

    private boolean tagMatched(JSONObject item, String tag) {
        String title = item.optString("title").toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
        String compact = title.replace(" ", "");
        String key = canonQuery(tag);
        List<String> aliases = tagAliasList(tag);
        boolean aliasHit = false;
        for (String alias : aliases) {
            if (aliasHitsTitle(title, compact, alias)) {
                aliasHit = true;
                break;
            }
        }
        for (String neg : negateFor(key)) {
            if (title.contains(neg) && !aliasHit) return false;
        }
        if (aliasHit) return true;
        if (PHRASE_ONLY.contains(key)) return false;
        List<String> tokens = distinctiveTokens(tag);
        boolean strong = false;
        for (String token : tokens) {
            if (!WEAK_SOLO.contains(token) && token.length() >= 4) strong = true;
        }
        if (!strong) return false;
        for (String token : tokens) {
            if (!tokenInItem(token, title, "", compact)) return false;
        }
        return tokensNear(title, tokens);
    }

    private int tagStrength(JSONObject item, String tag) {
        if (!tagMatched(item, tag)) return 0;
        String title = item.optString("title").toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
        String compact = title.replace(" ", "");
        for (String alias : tagAliasList(tag)) {
            String phrase = alias.toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
            if (!phrase.isEmpty() && title.contains(phrase)) return 3;
            String glued = phrase.replace(" ", "");
            if (!phrase.isEmpty() && glued.length() >= 5 && compact.contains(glued)) return 3;
        }
        return 2;
    }

    private List<String> queryAsTags(String query) {
        String key = canonQuery(query);
        if (!categoryPhrases(key).isEmpty()) return Arrays.asList(key);
        String blob = (query == null ? "" : query).toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
        List<String> found = new ArrayList<>();
        if (blob.isEmpty()) return found;
        String[] names = {
                "small tits", "large tits", "big tits", "medium tits", "natural tits", "perky tits",
                "large ass", "round ass", "black hair", "pink hair", "blue hair", "purple hair",
                "step-sis", "tramp stamp", "delivery guy", "maintenance man", "fly on the wall",
                "looking at camera", "over the shoulder", "third person", "behind camera",
                "full movie", "full scene", "reverse cowgirl", "prone bone", "mating press",
                "blonde", "brunette", "redhead", "platinum", "hotel", "motel", "car", "public",
                "homemade", "onlyfans", "cellphone", "snapchat", "petite", "socks", "amateur"
        };
        for (String name : names) {
            for (String alias : tagAliasList(name)) {
                String phrase = alias.toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
                if (phrase.isEmpty()) continue;
                if (Pattern.compile("\\b" + Pattern.quote(phrase) + "\\b").matcher(blob).find()) {
                    if (!found.contains(name)) found.add(name);
                    break;
                }
            }
            if (found.size() >= 4) break;
        }
        return found;
    }

    private List<String> parseTags(String raw) {
        List<String> tags = new ArrayList<>();
        if (raw == null || raw.trim().isEmpty()) return tags;
        for (String part : raw.split(",")) {
            String tag = part.trim().toLowerCase(Locale.US);
            if (tag.isEmpty() || tags.contains(tag)) continue;
            tags.add(tag);
            if (tags.size() >= 5) break;
        }
        return tags;
    }

    private List<JSONObject> rankItems(List<JSONObject> items, String query, List<String> tags) {
        List<String> tagList = tags == null ? new ArrayList<>() : new ArrayList<>(tags);
        if (tagList.isEmpty()) tagList.addAll(queryAsTags(query));
        if (!tagList.isEmpty()) {
            LinkedHashSet<String> all = new LinkedHashSet<>();
            for (String tag : tagList) all.addAll(rankingTerms(tag));
            List<String> terms = new ArrayList<>(all);
            List<int[]> ranks = new ArrayList<>();
            for (int i = 0; i < items.size(); i++) {
                JSONObject item = items.get(i);
                int hits = 0;
                int strength = 0;
                for (String tag : tagList) {
                    if (tagMatched(item, tag)) hits += 1;
                    strength += tagStrength(item, tag);
                }
                ranks.add(new int[]{hits, strength, relevanceScore(item, terms) + strength * 3, i});
            }
            ranks.sort((a, b) -> {
                if (a[0] != b[0]) return Integer.compare(b[0], a[0]);
                if (a[1] != b[1]) return Integer.compare(b[1], a[1]);
                return Integer.compare(b[2], a[2]);
            });
            int total = tagList.size();
            List<JSONObject> full = new ArrayList<>();
            List<JSONObject> almost = new ArrayList<>();
            List<JSONObject> some = new ArrayList<>();
            for (int[] row : ranks) {
                JSONObject item = items.get(row[3]);
                if (row[0] >= total) full.add(item);
                if (row[0] >= Math.max(1, total - 1)) almost.add(item);
                if (row[0] > 0) some.add(item);
            }
            if (!full.isEmpty()) return full;
            if (!almost.isEmpty()) return almost;
            return some;
        }
        return rankItemsSingle(items, query);
    }

    private List<JSONObject> rankItemsSingle(List<JSONObject> items, String query) {
        List<String> tokens = distinctiveTokens(query);
        List<String> terms = rankingTerms(query);
        List<int[]> ranks = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            JSONObject item = items.get(i);
            String title = item.optString("title").toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", " ").trim();
            String compact = title.replace(" ", "");
            int titleHits = 0;
            for (String token : tokens) {
                if (tokenInItem(token, title, "", compact)) titleHits += 1;
            }
            ranks.add(new int[]{titleHits, relevanceScore(item, terms) + titleHits * 4, i});
        }
        ranks.sort((a, b) -> {
            if (a[0] != b[0]) return Integer.compare(b[0], a[0]);
            return Integer.compare(b[1], a[1]);
        });
        if (tokens.isEmpty()) {
            List<JSONObject> all = new ArrayList<>();
            for (int[] row : ranks) all.add(items.get(row[2]));
            return all;
        }
        int needed = tokens.size() <= 3 ? tokens.size() : Math.max(2, (tokens.size() * 2 + 2) / 3);
        List<JSONObject> strong = new ArrayList<>();
        List<JSONObject> softer = new ArrayList<>();
        List<JSONObject> some = new ArrayList<>();
        for (int[] row : ranks) {
            JSONObject item = items.get(row[2]);
            if (row[0] >= needed) strong.add(item);
            if (needed > 1 && row[0] >= needed - 1) softer.add(item);
            if (row[0] > 0) some.add(item);
        }
        if (!strong.isEmpty()) return strong;
        if (!softer.isEmpty()) return softer;
        return some;
    }

    private String todayStamp() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    private File dailyFile(String source, int page) {
        String safe = (source == null || source.isEmpty() ? "all" : source)
                .toLowerCase(Locale.US).replaceAll("[^a-z0-9]+", "-");
        return new File(System.getProperty("java.io.tmpdir"),
                "gitvidx-daily-" + todayStamp() + "-" + safe + "-" + page + ".json");
    }

    private JSONObject loadDaily(String source, int page) {
        try {
            File file = dailyFile(source, page);
            if (!file.isFile()) return null;
            String text = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
            JSONObject data = new JSONObject(text);
            if (todayStamp().equals(data.optString("date")) && data.optJSONArray("items") != null
                    && data.optJSONArray("items").length() > 0) {
                return data;
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private void saveDaily(String source, int page, JSONObject payload) {
        File file = dailyFile(source, page);
        File dir = file.getParentFile();
        if (dir != null) {
            File[] old = dir.listFiles((d, name) -> name.startsWith("gitvidx-daily-") && name.endsWith(".json"));
            String stamp = todayStamp();
            if (old != null) {
                for (File item : old) {
                    if (!item.getName().contains(stamp)) {
                        //noinspection ResultOfMethodCallIgnored
                        item.delete();
                    }
                }
            }
        }
        try (FileOutputStream out = new FileOutputStream(file)) {
            out.write(payload.toString().getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignored) {
        }
    }

    private List<JSONObject> interleave(List<JSONObject> items) {
        Map<String, List<JSONObject>> buckets = new LinkedHashMap<>();
        for (JSONObject row : items) {
            String src = row.optString("source");
            buckets.computeIfAbsent(src, key -> new ArrayList<>()).add(row);
        }
        List<JSONObject> out = new ArrayList<>();
        boolean more = true;
        while (more) {
            more = false;
            for (List<JSONObject> bucket : buckets.values()) {
                if (!bucket.isEmpty()) {
                    out.add(bucket.remove(0));
                    more = true;
                }
            }
        }
        return out;
    }

    private SearchFn pick(String source) {
        switch (source) {
            case "pornhub": return this::pornhub;
            case "xvideos": return this::xvideos;
            case "xhamster": return this::xhamster;
            case "xnxx": return this::xnxx;
            case "redtube": return this::redtube;
            case "eporner": return this::eporner;
            case "xxxbunker": return this::xxxbunker;
            case "tnaflix": return this::tnaflix;
            case "drtuber": return this::drtuber;
            case "pornone": return this::pornone;
            case "okxxx": return this::okxxx;
            case "porn00": return this::porn00;
            case "xxxfiles": return this::xxxfiles;
            case "xmoviesforyou": return this::xmoviesforyou;
            case "whoreshub": return this::whoreshub;
            case "yespornvip": return this::yespornvip;
            case "justporn": return this::justporn;
            default: return this::pornhub;
        }
    }

    private List<JSONObject> pornhub(String query, int page) throws Exception {
        String url = isDaily(query)
                ? "https://www.pornhub.com/webmasters/search?thumbsize=large&ordering=featured&page=" + (page + 1)
                : "https://www.pornhub.com/webmasters/search?search=" + enc(query)
                + "&thumbsize=large&page=" + (page + 1);
        JSONObject data = new JSONObject(fetchText(url));
        JSONArray rows = data.optJSONArray("videos");
        List<JSONObject> items = new ArrayList<>();
        if (rows == null) {
            return items;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String pageUrl = row.optString("url");
            String embed = "";
            int at = pageUrl.indexOf("viewkey=");
            if (at >= 0) {
                String key = pageUrl.substring(at + 8).split("&")[0];
                embed = "https://www.pornhub.com/embed/" + key;
            }
            items.add(item("Pornhub", "pornhub", row.optString("title"), pageUrl,
                    row.optString("default_thumb", row.optString("thumb")), embed, row.optString("duration")));
        }
        return items;
    }

    private List<JSONObject> youporn(String query, int page) throws Exception {
        String url = "https://www.youporn.com/api/webmasters/search?search=" + enc(query)
                + "&thumbsize=large&page=" + (page + 1);
        JSONObject data = new JSONObject(fetchText(url));
        JSONArray rows = data.optJSONArray("video");
        if (rows == null) {
            rows = data.optJSONArray("videos");
        }
        List<JSONObject> items = new ArrayList<>();
        if (rows == null) {
            return items;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String pageUrl = row.optString("url");
            String embed = row.optString("embed");
            items.add(item("YouPorn", "youporn", row.optString("title"), pageUrl,
                    row.optString("default_thumb", row.optString("thumb")), embed, row.optString("duration")));
        }
        return items;
    }

    private List<JSONObject> redtube(String query, int page) throws Exception {
        String url = isDaily(query)
                ? "https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&ordering=featured&thumbsize=medium&page=" + (page + 1)
                : "https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&search="
                + enc(query) + "&thumbsize=medium&page=" + (page + 1);
        JSONObject data = new JSONObject(fetchText(url));
        JSONArray rows = data.optJSONArray("videos");
        List<JSONObject> items = new ArrayList<>();
        if (rows == null) {
            return items;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject wrap = rows.optJSONObject(i);
            JSONObject row = wrap == null ? null : wrap.optJSONObject("video");
            if (row == null) continue;
            String id = row.optString("video_id");
            String embed = id.isEmpty() ? "" : "https://embed.redtube.com/?id=" + id;
            items.add(item("RedTube", "redtube", row.optString("title"), row.optString("url"),
                    row.optString("default_thumb", row.optString("thumb")), embed, row.optString("duration")));
        }
        return items;
    }

    private List<JSONObject> eporner(String query, int page) throws Exception {
        String url = isDaily(query)
                ? "https://www.eporner.com/api/v2/video/search/?query=&per_page=20&page=" + (page + 1)
                + "&thumbsize=medium&order=top-weekly&gay=0&lq=1&format=json"
                : "https://www.eporner.com/api/v2/video/search/?query=" + enc(query)
                + "&per_page=20&page=" + (page + 1) + "&thumbsize=medium&order=latest&gay=0&lq=1&format=json";
        JSONObject data = new JSONObject(fetchText(url));
        JSONArray rows = data.optJSONArray("videos");
        List<JSONObject> items = new ArrayList<>();
        if (rows == null) {
            return items;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null) continue;
            String thumb = "";
            Object defaultThumb = row.opt("default_thumb");
            if (defaultThumb instanceof JSONObject) {
                thumb = ((JSONObject) defaultThumb).optString("src");
            } else if (defaultThumb != null) {
                thumb = String.valueOf(defaultThumb);
            }
            String embed = row.optString("embed");
            if (embed.isEmpty() && row.has("id")) {
                embed = "https://www.eporner.com/embed/" + row.optString("id");
            }
            items.add(item("Eporner", "eporner", row.optString("title"), row.optString("url"),
                    thumb, embed, row.optString("length_min")));
        }
        return items;
    }

    private List<JSONObject> xvideos(String query, int page) throws Exception {
        String url = isDaily(query)
                ? (page == 0 ? "https://www.xvideos.com/" : "https://www.xvideos.com/new/" + (page + 1))
                : "https://www.xvideos.com/?k=" + enc(query) + "&p=" + page;
        return htmlVideos(
                url,
                "XVideos",
                "xvideos",
                Pattern.compile("href=\"(/video[^\"]+)\"[\\s\\S]{0,900}?data-src=\"(https://[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                "https://www.xvideos.com",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private List<JSONObject> xnxx(String query, int page) throws Exception {
        String extra = page == 0 ? "" : ("/" + page);
        String url = isDaily(query)
                ? "https://www.xnxx.com/todays-selection" + extra
                : "https://www.xnxx.com/search/" + enc(query) + extra;
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        List<JSONObject> items = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        Matcher matcher = Pattern.compile(
                "href=\"(/video-[^\"]+)\"[\\s\\S]{0,900}?data-src=\"(https://[^\"]+)\"",
                Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 48) {
            String thumb = cleanThumb(matcher.group(2));
            if (thumb.isEmpty()) continue;
            String pageUrl = "https://www.xnxx.com" + matcher.group(1);
            if (!seen.add(pageUrl)) continue;
            String title = matcher.group(1).replaceAll(".*/", "").replace("-", " ").replace("_", " ");
            items.add(item("XNXX", "xnxx", title, pageUrl, thumb, "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> xhamster(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://xhamster.com/best/daily" : "https://xhamster.com/best/daily/" + (page + 1);
        } else {
            String extra = page == 0 ? "" : ("?page=" + (page + 1));
            url = "https://xhamster.com/search/" + enc(query) + extra;
        }
        return htmlVideos(
                url,
                "xHamster",
                "xhamster",
                Pattern.compile("href=\"(https://xhamster\\.com/videos/[^\"]+)\"[^>]*>.*?(?:src|data-src)=\"(https://[^\"]+)\"", Pattern.CASE_INSENSITIVE | Pattern.DOTALL),
                "",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private String cleanDuration(String raw) {
        if (raw == null) return "";
        String text = raw.replaceAll("<[^>]+>", " ").replaceAll("\\s+", " ").trim();
        if (text.isEmpty()) return "";
        if (text.matches("\\d{1,5}")) {
            int total = Integer.parseInt(text);
            if (total <= 0 || total > 12 * 3600) return "";
            int hours = total / 3600;
            int minutes = (total % 3600) / 60;
            int seconds = total % 60;
            return hours > 0
                    ? hours + ":" + String.format(Locale.US, "%02d:%02d", minutes, seconds)
                    : minutes + ":" + String.format(Locale.US, "%02d", seconds);
        }
        java.util.regex.Matcher match = Pattern.compile("(?:(\\d{1,2}):)?(\\d{1,2}):(\\d{2})").matcher(text);
        if (match.find()) {
            String hour = match.group(1);
            int minute = Integer.parseInt(match.group(2));
            int second = Integer.parseInt(match.group(3));
            if (second > 59) return "";
            if (hour != null) return Integer.parseInt(hour) + ":" + String.format(Locale.US, "%02d:%02d", minute, second);
            return minute + ":" + String.format(Locale.US, "%02d", second);
        }
        match = Pattern.compile("(\\d{1,3})\\s*(?:min|mins|minutes)\\b", Pattern.CASE_INSENSITIVE).matcher(text);
        if (match.find()) return Integer.parseInt(match.group(1)) + ":00";
        return "";
    }

    private String pickDuration(String chunk) {
        if (chunk == null || chunk.isEmpty()) return "";
        Matcher labeled = Pattern.compile("(?:class|id)=\"[^\"]*(?:duration|runtime|video-time|video-duration|length)[^\"]*\"[^>]*>([^<]{1,32})", Pattern.CASE_INSENSITIVE).matcher(chunk);
        while (labeled.find()) {
            String got = cleanDuration(labeled.group(1));
            if (!got.isEmpty()) return got;
        }
        Matcher times = Pattern.compile("(?<!\\d)(\\d{1,2}:\\d{2}(?::\\d{2})?)(?!\\d)").matcher(chunk);
        String last = "";
        while (times.find()) {
            String got = cleanDuration(times.group(1));
            if (!got.isEmpty()) last = got;
        }
        if (!last.isEmpty()) return last;
        Matcher mins = Pattern.compile("(\\d{1,3})\\s*(?:min|mins|minutes)\\b", Pattern.CASE_INSENSITIVE).matcher(chunk);
        return mins.find() ? cleanDuration(mins.group(0)) : "";
    }

    private List<JSONObject> fillDurations(List<JSONObject> items, String body) {
        if (body == null) return items;
        for (JSONObject item : items) {
            String current = cleanDuration(item.optString("duration"));
            if (!current.isEmpty()) {
                try { item.put("duration", current); } catch (Exception ignored) {}
                continue;
            }
            String needle = item.optString("thumb");
            if (needle.isEmpty()) needle = item.optString("page");
            int idx = needle.isEmpty() ? -1 : body.indexOf(needle.substring(0, Math.min(90, needle.length())));
            if (idx < 0) continue;
            int from = Math.max(0, idx - 400);
            int to = Math.min(body.length(), idx + 2800);
            try { item.put("duration", pickDuration(body.substring(from, to))); } catch (Exception ignored) {}
        }
        return items;
    }

    private List<JSONObject> homemadegalore(String query, int page) {
        String extra = page > 0 ? ("?page=" + (page + 1)) : "";
        String[] urls = {
                "https://www.homemadegalore.com/search/" + encodeSafe(query) + extra,
                "https://homemadegalore.com/search/" + encodeSafe(query) + extra,
                "https://www.homemadegalore.com/search/" + encodeSafe(query) + "/" + extra
        };
        for (String url : urls) {
            try {
                String body = fetchHtml(url, DESKTOP_UA);
                List<JSONObject> items = new ArrayList<>();
                Matcher matcher = Pattern.compile(
                        "href=\"(/out/\\?l=[^\"]+)\"[^>]*title=\"([^\"]+)\"[^>]*>\\s*<img[^>]+src=\"(https://c\\d+\\.ttcache\\.com/[^\"]+)\"",
                        Pattern.CASE_INSENSITIVE).matcher(body);
                while (matcher.find() && items.size() < 40) {
                    items.add(item("HomemadeGalore", "homemadegalore", matcher.group(2),
                            "https://www.homemadegalore.com" + matcher.group(1).replace("&amp;", "&"),
                            cleanThumb(matcher.group(3)), "", ""));
                }
                if (!items.isEmpty()) {
                    return fillDurations(items, body);
                }
            } catch (Exception ignored) {
                // try the next URL
            }
        }
        return new ArrayList<>();
    }

    private String encodeSafe(String value) {
        try {
            return enc(value);
        } catch (Exception error) {
            return value.replace(" ", "+");
        }
    }

    private String cleanThumb(String url) {
        if (url == null || url.isEmpty()) return "";
        if (url.startsWith("//")) url = "https:" + url;
        String low = url.toLowerCase(Locale.US);
        if (low.contains("blank.gif") || low.contains("lightbox-blank") || low.contains("placeholder")
                || low.contains("pixel.gif") || low.contains("1x1")) {
            return "";
        }
        url = url.replace("ei-ph.rdtcdn.com", "ei.phncdn.com").replace(".rdtcdn.com", ".phncdn.com");
        return url;
    }

    private List<JSONObject> hqporner(String query, int page) throws Exception {
        String extra = page > 0 ? ("&p=" + (page + 1)) : "";
        String body = fetchText("https://hqporner.com/?q=" + enc(query) + extra);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile(
                "href=\"(/hdporn/[^\"]+)\"[\\s\\S]{0,900}?defaultImage\\(\"(//[^\"]+)\"",
                Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 40) {
            String pageUrl = "https://hqporner.com" + matcher.group(1);
            String title = matcher.group(1).replaceAll(".*/", "").replace(".html", "").replaceFirst("^\\d+-", "").replace("_", " ");
            items.add(item("HQPorner", "hqporner", title, pageUrl, cleanThumb(matcher.group(2)), "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> xxxbunker(String query, int page) throws Exception {
        String extra = page > 0 ? ("/" + (page + 1)) : "";
        String url = isDaily(query)
                ? "https://xxxbunker.com/" + extra.replaceFirst("^/", "")
                : "https://xxxbunker.com/search/" + enc(query).replace("%20", "+") + extra;
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile(
                "(?:src|data-src)=\"https://thumbs\\.xxxbunker\\.com/(\\d+)\\.jpg\"[^>]*alt=\"([^\"]*)\"",
                Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 40) {
            String id = matcher.group(1);
            String pageUrl = "https://xxxbunker.com/" + id;
            items.add(item("XXXBunker", "xxxbunker", matcher.group(2), pageUrl, "https://thumbs.xxxbunker.com/" + id + ".jpg", "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> tnaflix(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page > 0 ? "https://www.tnaflix.com/?page=" + (page + 1) : "https://www.tnaflix.com/";
        } else {
            String extra = page > 0 ? ("&page=" + (page + 1)) : "";
            url = "https://www.tnaflix.com/search.php?what=" + enc(query) + extra;
        }
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile("(<div data-vid=\"\\d+\"[\\s\\S]{0,3000}?</div>\\s*</div>)", Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 40) {
            String chunk = matcher.group(1);
            Matcher href = Pattern.compile("href=\"(https://www\\.tnaflix\\.com/[^\"]+/video\\d+)\"").matcher(chunk);
            Matcher thumb = Pattern.compile("(?:data-src|src)=\"(https://(?:cdnl|img)\\.tnaflix\\.com/[^\"]+\\.jpg)\"").matcher(chunk);
            if (!href.find()) continue;
            String pageUrl = href.group(1);
            String title = pageUrl.replaceAll("/video\\d+$", "").replaceAll(".*/", "").replace("-", " ");
            items.add(item("TNAflix", "tnaflix", title, pageUrl, thumb.find() ? cleanThumb(thumb.group(1)) : "", "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> drtuber(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://www.drtuber.com/" : "https://www.drtuber.com/latest-updates/" + (page + 1);
        } else {
            String extra = page > 0 ? ("/" + (page + 1)) : "";
            url = "https://www.drtuber.com/search/videos/" + enc(query) + extra;
        }
        return htmlVideos(
                url,
                "DrTuber",
                "drtuber",
                Pattern.compile("href=\"(/video/\\d+/[^\"]+)\"[^>]*>\\s*<img[^>]+src=\"(https://[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                "https://www.drtuber.com",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private List<JSONObject> sunporno(String query, int page) throws Exception {
        String extra = page > 0 ? ((page + 1) + "/") : "";
        return htmlVideos(
                "https://www.sunporno.com/search/" + enc(query) + "/" + extra,
                "SunPorno",
                "sunporno",
                Pattern.compile("href=\"(https://www\\.sunporno\\.com/v/\\d+/[^\"]+)\"[\\s\\S]{0,500}?src=\"(https://acdn\\.sunporno\\.com/[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                ""
        );
    }

    private List<JSONObject> pornone(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://www.pornone.com/" : "https://www.pornone.com/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("/" + (page + 1)) : "";
            url = "https://www.pornone.com/search" + extra + "/?q=" + enc(query);
        }
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        Map<String, String> thumbs = new LinkedHashMap<>();
        Matcher tm = Pattern.compile("(https://th-eu\\d+\\.pornone\\.com/t/\\d+/(\\d+)/[^\"\\s]+)").matcher(body);
        while (tm.find()) thumbs.put(tm.group(2), cleanThumb(tm.group(1)));
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile("href=\"(https://(?:www\\.)?pornone\\.com/[^\"]+/(\\d+)/)\"", Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 40) {
            String pageUrl = matcher.group(1);
            String title = pageUrl.replaceAll("/+$", "").replaceAll("/\\d+$", "").replaceAll(".*/", "").replace("-", " ");
            items.add(item("PornOne", "pornone", title, pageUrl, thumbs.getOrDefault(matcher.group(2), ""), "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> tube8(String query, int page) throws Exception {
        String extra = page > 0 ? ("&page=" + (page + 1)) : "";
        return htmlVideos(
                "https://www.tube8.com/searches.html?q=" + enc(query) + extra,
                "Tube8",
                "tube8",
                Pattern.compile("href=\"(https://www\\.tube8\\.com/[a-z0-9-]+/[a-z0-9-]+/\\d+/)\"[\\s\\S]{0,700}?(?:data-src|src)=\"(https://[^\"]+\\.(?:jpg|jpeg|webp))\"", Pattern.CASE_INSENSITIVE),
                ""
        );
    }

    private List<JSONObject> okxxx(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://ok.xxx/" : "https://ok.xxx/latest-updates/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("?from_videos=" + (page + 1)) : "";
            url = "https://ok.xxx/search/" + enc(query) + "/" + extra;
        }
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile("href=\"(/video/\\d+/)\"[^>]*title=\"([^\"]*)\"[\\s\\S]{0,700}?data-original=\"(https://[^\"]+)\"", Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 40) {
            items.add(item("OK.xxx", "okxxx", matcher.group(2), "https://ok.xxx" + matcher.group(1), cleanThumb(matcher.group(3)), "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> porn00(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://www.porn00.org/latest/" : "https://www.porn00.org/latest/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ((page + 1) + "/") : "";
            url = "https://www.porn00.org/q/" + enc(query) + "/" + extra;
        }
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile("href=\"(https://www.porn00.org/video/[^\"]+)\"[^>]*title=\"([^\"]*)\"[\\s\\S]{0,600}?data-original=\"(https://[^\"]+)\"", Pattern.CASE_INSENSITIVE).matcher(body);
        while (matcher.find() && items.size() < 40) {
            items.add(item("Porn00", "porn00", matcher.group(2), matcher.group(1), cleanThumb(matcher.group(3)), "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> xxxfiles(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://www.xxxfiles.com/" : "https://www.xxxfiles.com/page/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("&page=" + (page + 1)) : "";
            url = "https://www.xxxfiles.com/?s=" + enc(query) + extra;
        }
        return htmlVideos(
                url,
                "XXXFiles",
                "xxxfiles",
                Pattern.compile("href=\"(https://www.xxxfiles.com/videos/\\d+/[^\"]+)\"[\\s\\S]{0,500}?src=\"(https://img.xxxfiles.com/[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                "",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private List<JSONObject> xmoviesforyou(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://xmoviesforyou.com/" : "https://xmoviesforyou.com/page/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("&paged=" + (page + 1)) : "";
            url = "https://xmoviesforyou.com/?s=" + enc(query) + extra;
        }
        return htmlVideos(
                url,
                "XMoviesForYou",
                "xmoviesforyou",
                Pattern.compile("href=\"(/[a-z0-9-]+)\"[^>]*>[\\s\\S]{0,500}?src=\"(https://xmoviescdn\\.online/[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                "https://xmoviesforyou.com",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private List<JSONObject> whoreshub(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://www.whoreshub.com/" : "https://www.whoreshub.com/latest-updates/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("?from_videos=" + (page + 1)) : "";
            url = "https://www.whoreshub.com/search/" + enc(query) + "/" + extra;
        }
        String body = isDaily(query) ? fetchHtml(url, DESKTOP_UA) : fetchText(url);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile("href=\"(https://www.whoreshub.com/videos/(\\d+)/[^\"]+)\"").matcher(body);
        while (matcher.find() && items.size() < 40) {
            int num = Integer.parseInt(matcher.group(2));
            int bucket = (num / 1000) * 1000;
            String title = matcher.group(1).replaceAll("/+$", "").replaceAll(".*/", "").replace("-", " ");
            String thumb = "https://www.whoreshub.com/contents/videos_screenshots/" + bucket + "/" + num + "/320x180/1.jpg";
            items.add(item("WhoresHub", "whoreshub", title, matcher.group(1), thumb, "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> yespornvip(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://yespornvip.com/" : "https://yespornvip.com/page/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("&paged=" + (page + 1)) : "";
            url = "https://yespornvip.com/?s=" + enc(query) + extra;
        }
        return htmlVideos(
                url,
                "YesPornVIP",
                "yespornvip",
                Pattern.compile("href=\"(https://yespornvip.com/[a-z0-9-]+/)\"[\\s\\S]{0,800}?(?:data-src|src)=\"(https://yespornvip.com/wp-content/uploads/thumbsx/[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                "",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private List<JSONObject> justporn(String query, int page) throws Exception {
        String url;
        if (isDaily(query)) {
            url = page == 0 ? "https://www.justporn.to/" : "https://www.justporn.to/page/" + (page + 1) + "/";
        } else {
            String extra = page > 0 ? ("page/" + (page + 1) + "/") : "";
            url = "https://www.justporn.to/search/" + enc(query) + "/" + extra;
        }
        return htmlVideos(
                url,
                "JustPorn",
                "justporn",
                Pattern.compile("href=\"(https://(?:www\\.)?justporn.to/[a-z0-9-]+/)\"[\\s\\S]{0,700}?src=\"(https://justporn.to/cover_upload/[^\"]+)\"", Pattern.CASE_INSENSITIVE),
                "",
                isDaily(query) ? DESKTOP_UA : BROWSER_UA
        );
    }

    private List<JSONObject> porndig(String query, int page) throws Exception {
        String extra = page > 0 ? ("&page=" + (page + 1)) : "";
        String body = fetchText("https://www.porndig.com/" + enc(query) + "?q=" + enc(query) + extra);
        List<JSONObject> items = new ArrayList<>();
        Matcher matcher = Pattern.compile("data-video_id=\"(\\d+)\"[\\s\\S]{0,200}?(?:data-src|src)=\"(https://image-cdn.porndig.com/[^\"]+)\"").matcher(body);
        while (matcher.find() && items.size() < 40) {
            items.add(item("PornDig", "porndig", "Video " + matcher.group(1), "https://www.porndig.com/videos/" + matcher.group(1), cleanThumb(matcher.group(2)), "", ""));
        }
        return fillDurations(items, body);
    }

    private List<JSONObject> htmlVideos(String url, String provider, String source, Pattern pattern, String prefix) throws Exception {
        return htmlVideos(url, provider, source, pattern, prefix, BROWSER_UA);
    }

    private List<JSONObject> htmlVideos(String url, String provider, String source, Pattern pattern, String prefix, String ua) throws Exception {
        String body = fetchHtml(url, ua);
        Matcher matcher = pattern.matcher(body);
        List<JSONObject> items = new ArrayList<>();
        Map<String, Boolean> seen = new LinkedHashMap<>();
        while (matcher.find() && items.size() < 40) {
            String path = matcher.group(1);
            String thumb = matcher.group(2);
            String pageUrl = path.startsWith("http") ? path.split("\\?")[0] : prefix + path;
            if (seen.containsKey(pageUrl)) {
                continue;
            }
            seen.put(pageUrl, true);
            String title = pageUrl.replaceAll(".*/", "").replace("-", " ").replace("_", " ");
            if (cleanThumb(thumb).isEmpty()) continue;
            items.add(item(provider, source, title, pageUrl, cleanThumb(thumb), "", ""));
        }
        return fillDurations(items, body);
    }

    private boolean hostBlocked(String url) {
        try {
            String host = new URL(url).getHost();
            if (host == null) return true;
            host = host.toLowerCase(Locale.US);
            if (host.startsWith("www.")) host = host.substring(4);
            for (String bit : BLOCKED_HOST_BITS) {
                if (host.contains(bit)) return true;
            }
            return false;
        } catch (Exception ignored) {
            return url != null && !url.isEmpty();
        }
    }

    private boolean allowedItem(JSONObject row) {
        String blob = row.optString("title") + " " + row.optString("page") + " " + row.optString("url");
        if (blockedQuery(blob) != null) return false;
        return !hostBlocked(row.optString("page")) && !hostBlocked(row.optString("url"));
    }

    private JSONObject item(String provider, String source, String title, String page, String thumb, String embed, String duration) throws Exception {
        JSONObject row = new JSONObject();
        String id = source + "-" + sha1(page == null ? title : page).substring(0, 16);
        row.put("id", id);
        row.put("provider", provider);
        row.put("source", source);
        row.put("title", title == null ? "" : (title.length() > 180 ? title.substring(0, 180) : title));
        row.put("page", page == null ? "" : page);
        row.put("url", page == null ? "" : page);
        row.put("thumb", cleanThumb(thumb));
        row.put("embed", embed == null ? "" : embed);
        row.put("duration", cleanDuration(duration == null ? "" : duration));
        return row;
    }

    private String fetchText(String url) throws Exception {
        return fetchHtml(url, BROWSER_UA);
    }

    private String fetchHtml(String url, String ua) throws Exception {
        HttpURLConnection connection = open(new URL(url), "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");
        connection.setRequestProperty("User-Agent", ua);
        connection.setRequestProperty("Accept-Language", "en-US,en;q=0.9");
        try {
            int code = connection.getResponseCode();
            InputStream stream = code >= 400 ? connection.getErrorStream() : connection.getInputStream();
            String body = new String(readLimited(stream, 4_000_000), StandardCharsets.UTF_8);
            if (code >= 400) {
                throw new IllegalStateException("HTTP " + code);
            }
            return body;
        } finally {
            connection.disconnect();
        }
    }

    private HttpURLConnection open(URL url, String accept) throws Exception {
        return open(url, accept, url.getProtocol() + "://" + url.getHost() + "/");
    }

    private HttpURLConnection open(URL url, String accept, String referer) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(12000);
        connection.setInstanceFollowRedirects(true);
        connection.setRequestProperty("User-Agent", BROWSER_UA);
        connection.setRequestProperty("Accept", accept);
        if (referer != null && referer.startsWith("http")) {
            connection.setRequestProperty("Referer", referer);
        }
        return connection;
    }

    private boolean isPublicHost(String host) {
        try {
            InetAddress[] addresses = InetAddress.getAllByName(host);
            for (InetAddress address : addresses) {
                if (address.isAnyLocalAddress() || address.isLoopbackAddress()
                        || address.isLinkLocalAddress() || address.isSiteLocalAddress()) {
                    return false;
                }
            }
            return addresses.length > 0;
        } catch (Exception ignored) {
            return false;
        }
    }

    private byte[] readLimited(InputStream stream, int max) throws Exception {
        if (stream == null) return new byte[0];
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int read;
        int total = 0;
        while ((read = stream.read(chunk)) != -1) {
            total += read;
            if (total > max) break;
            buffer.write(chunk, 0, read);
        }
        return buffer.toByteArray();
    }

    private String enc(String value) throws Exception {
        return URLEncoder.encode(value, StandardCharsets.UTF_8.name());
    }

    private String sha1(String value) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-1").digest(value.getBytes(StandardCharsets.UTF_8));
        StringBuilder hex = new StringBuilder();
        for (byte part : digest) {
            hex.append(String.format(Locale.US, "%02x", part));
        }
        return hex.toString();
    }

    private interface SearchFn {
        List<JSONObject> run(String query, int page) throws Exception;
    }

    private static final class NamedResult {
        final String name;
        final List<JSONObject> items;

        NamedResult(String name, List<JSONObject> items, String ignored) {
            this.name = name;
            this.items = items;
        }
    }

    private static final class NamedSearch {
        final String name;
        final SearchFn fn;

        NamedSearch(String name, SearchFn fn) {
            this.name = name;
            this.fn = fn;
        }
    }

    static final class ImageResult {
        final String contentType;
        final byte[] body;

        ImageResult(String contentType, byte[] body) {
            this.contentType = contentType;
            this.body = body;
        }
    }
}

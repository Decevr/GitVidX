import Foundation
import CryptoKit

struct ImageProxy {
    let data: Data
    let mime: String
    let status: Int
}

final class SearchEngine {
    private let desktopUA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    private let mobileUA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    private let dailyQ = "__daily__"
    private let blockReason = "That search is blocked. GitVidX only shows legal, consensual, 18+ videos. No leaks, hidden cameras, or non-consensual content."
    private let stop: Set<String> = [
        "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "plus",
        "hair", "sex", "fuck", "video", "style", "position", "man", "guy",
        "view", "camera", "cam", "shot", "angle"
    ]
    private let phrases: [String: String] = [
        "amateur": "amateur", "milf": "milf", "lesbian": "lesbian", "blonde": "blonde",
        "brunette": "brunette", "anal": "anal", "pov": "pov", "solo": "solo",
        "hardcore": "hardcore", "blowjob": "blowjob", "creampie": "creampie",
        "big tits": "big tits", "asian": "asian", "latina": "latina", "threesome": "threesome",
        "feet": "feet", "socks": "socks", "cheating": "cheating wife", "cuckold": "cuckold",
        "teen": "teen", "step-sis": "stepsister", "homemade": "homemade", "onlyfans": "onlyfans",
        "ai": "ai generated", "missionary": "missionary", "doggy": "doggy style",
        "cowgirl": "cowgirl", "reverse cowgirl": "reverse cowgirl", "spooning": "spooning",
        "standing": "standing sex", "69": "69", "prone bone": "prone bone",
        "mating press": "mating press", "lotus": "lotus position", "piledriver": "piledriver",
        "butterfly": "butterfly position", "amazon": "amazon position", "wheelbarrow": "wheelbarrow",
        "anvil": "anvil position", "facesitting": "facesitting", "scissoring": "scissoring",
        "sideways": "sideways fuck", "legs up": "legs up", "bent over": "bent over",
        "full nelson": "full nelson", "against wall": "against the wall", "chair": "chair sex",
        "michigan": "michigan", "slipped in": "slipped it in",
        "redhead": "redhead", "black hair": "black hair", "auburn": "auburn",
        "platinum": "platinum blonde", "grey": "grey hair", "pink hair": "pink hair",
        "blue hair": "blue hair", "purple hair": "purple hair", "cellphone": "cellphone video",
        "snapchat": "snapchat", "hotel": "hotel sex", "motel": "motel sex", "car": "car sex",
        "public": "public sex", "sneaky": "sneaky sex", "quickie": "quickie",
        "tramp stamp": "tramp stamp", "delivery guy": "delivery guy",
        "maintenance man": "maintenance man", "fly on the wall": "fly on the wall",
        "third person": "third person view", "close up": "close up", "full body": "full body",
        "overhead": "overhead view", "low angle": "low angle", "side view": "side view",
        "behind camera": "from behind camera", "face cam": "face cam",
        "looking at camera": "looking at camera", "mirror": "mirror sex",
        "handheld": "handheld camera", "tripod": "tripod camera", "gopro": "gopro",
        "selfie cam": "selfie", "two camera": "two camera", "cinematic": "cinematic",
        "over the shoulder": "over the shoulder", "wide shot": "wide shot"
    ]

    func search(url: URL) -> Data {
        let q = queryItem(url, "q") ?? "amateur"
        if blocked(q) {
            return json(["error": blockReason, "items": []], statusHint: 400)
        }
        let source = queryItem(url, "source") ?? "all"
        let page = Int(queryItem(url, "page") ?? "0") ?? 0
        let refresh = queryItem(url, "refresh") == "1"
        let tags = (queryItem(url, "tags") ?? "").split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces).lowercased() }.filter { !$0.isEmpty }
        let payload = runSearch(q, source: source, page: max(0, page), refresh: refresh, tags: Array(tags.prefix(5)))
        return json(payload)
    }

    func fetchImage(url: URL) -> ImageProxy {
        guard let target = queryItem(url, "url"), let remote = URL(string: target), remote.scheme == "https" else {
            return ImageProxy(data: Data(), mime: "text/plain", status: 400)
        }
        var ref = queryItem(url, "ref") ?? ""
        let host = (remote.host ?? "").lowercased()
        if ref.isEmpty {
            if host.contains("xvideos") { ref = "https://www.xvideos.com/" }
            else if host.contains("xnxx") { ref = "https://www.xnxx.com/" }
            else if host.contains("xhamster") { ref = "https://xhamster.com/" }
            else if !host.isEmpty { ref = "https://\(host)/" }
        }
        let fetched = fetchBytes(remote.absoluteString, accept: "image/avif,image/webp,image/*,*/*;q=0.8", referer: ref)
        guard fetched.status < 400, !fetched.data.isEmpty else {
            return ImageProxy(data: Data(), mime: "text/plain", status: 502)
        }
        var mime = fetched.mime
        if mime.isEmpty || (!mime.contains("image") && !mime.contains("octet-stream")) {
            mime = "image/jpeg"
        }
        return ImageProxy(data: fetched.data, mime: mime.split(separator: ";").first.map(String.init) ?? mime, status: 200)
    }

    private func runSearch(_ query: String, source: String, page: Int, refresh: Bool, tags: [String]) -> [String: Any] {
        let daily = isDaily(query)
        if daily, !refresh, let cached = loadDaily(source: source, page: page) {
            return cached
        }
        let send: String
        if daily {
            send = query
        } else if !tags.isEmpty {
            send = combine(tags)
        } else {
            send = expand(query)
        }
        let jobs: [String] = {
            let all = ["pornhub", "xvideos", "xhamster", "xnxx", "redtube", "eporner", "xxxbunker", "tnaflix", "drtuber", "pornone", "okxxx", "porn00", "xxxfiles", "xmoviesforyou", "whoreshub", "yespornvip", "justporn"]
            if source == "all" || source.isEmpty || !all.contains(source) { return all }
            return [source]
        }()
        let group = DispatchGroup()
        let lock = NSLock()
        var items: [[String: String]] = []
        var used: [String] = []
        var errors: [String] = []
        for name in jobs {
            group.enter()
            DispatchQueue.global(qos: .userInitiated).async {
                defer { group.leave() }
                do {
                    let found = try self.site(name, query: send.isEmpty ? "amateur" : send, page: page).filter { self.allowed($0) }
                    if !found.isEmpty {
                        lock.lock()
                        items.append(contentsOf: found)
                        used.append(name)
                        lock.unlock()
                    }
                } catch {
                    lock.lock()
                    errors.append("\(name): \(error.localizedDescription)")
                    lock.unlock()
                }
            }
        }
        _ = group.wait(timeout: .now() + 22)
        var unique: [[String: String]] = []
        var seen = Set<String>()
        for row in items {
            let key = row["page"] ?? row["id"] ?? ""
            if key.isEmpty || seen.contains(key) { continue }
            seen.insert(key)
            unique.append(row)
        }
        if daily {
            unique = interleave(unique)
        } else {
            unique = rank(unique, query: query, tags: tags)
        }
        var payload: [String: Any] = [
            "query": query,
            "items": unique,
            "next": !unique.isEmpty && !daily,
            "sources": used,
            "mode": daily ? "daily" : "search",
            "error": unique.isEmpty && !errors.isEmpty ? errors.joined(separator: "; ") : NSNull()
        ]
        payload["date"] = daily ? today() : NSNull()
        if daily, !unique.isEmpty {
            saveDaily(source: source, page: page, payload: payload)
        }
        return payload
    }

    private func site(_ name: String, query: String, page: Int) throws -> [[String: String]] {
        let daily = isDaily(query)
        switch name {
        case "pornhub":
            let url = daily
                ? "https://www.pornhub.com/webmasters/search?thumbsize=large&ordering=featured&page=\(page + 1)"
                : "https://www.pornhub.com/webmasters/search?search=\(enc(query))&thumbsize=large&page=\(page + 1)"
            return jsonVideos(url, provider: "Pornhub", source: "pornhub", list: "videos") { row in
                let pageUrl = row["url"] as? String ?? ""
                var embed = ""
                if let range = pageUrl.range(of: "viewkey=") {
                    let key = pageUrl[range.upperBound...].split(separator: "&").first.map(String.init) ?? ""
                    if !key.isEmpty { embed = "https://www.pornhub.com/embed/\(key)" }
                }
                return self.item("Pornhub", "pornhub", self.text(row["title"]), pageUrl, self.text(row["default_thumb"]) ?? self.text(row["thumb"]), embed, self.text(row["duration"]))
            }
        case "redtube":
            let url = daily
                ? "https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&ordering=featured&thumbsize=medium&page=\(page + 1)"
                : "https://api.redtube.com/?data=redtube.Videos.searchVideos&output=json&search=\(enc(query))&thumbsize=medium&page=\(page + 1)"
            return jsonVideos(url, provider: "RedTube", source: "redtube", list: "videos") { wrap in
                let row = (wrap["video"] as? [String: Any]) ?? wrap
                let id = "\(row["video_id"] ?? "")"
                let embed = id.isEmpty ? "" : "https://embed.redtube.com/?id=\(id)"
                return self.item("RedTube", "redtube", self.text(row["title"]), self.text(row["url"]), self.text(row["default_thumb"]) ?? self.text(row["thumb"]), embed, self.text(row["duration"]))
            }
        case "eporner":
            let url = daily
                ? "https://www.eporner.com/api/v2/video/search/?query=&per_page=20&page=\(page + 1)&thumbsize=medium&order=top-weekly&gay=0&lq=1&format=json"
                : "https://www.eporner.com/api/v2/video/search/?query=\(enc(query))&per_page=20&page=\(page + 1)&thumbsize=medium&order=latest&gay=0&lq=1&format=json"
            return jsonVideos(url, provider: "Eporner", source: "eporner", list: "videos") { row in
                var thumb = ""
                if let def = row["default_thumb"] as? [String: Any] { thumb = def["src"] as? String ?? "" }
                else if let def = row["default_thumb"] as? String { thumb = def }
                var embed = row["embed"] as? String ?? ""
                if embed.isEmpty, let id = row["id"] { embed = "https://www.eporner.com/embed/\(id)" }
                return self.item("Eporner", "eporner", self.text(row["title"]), self.text(row["url"]), thumb, embed, self.text(row["length_min"]) ?? self.text(row["length_sec"]))
            }
        case "xvideos":
            let url = daily ? (page == 0 ? "https://www.xvideos.com/" : "https://www.xvideos.com/new/\(page + 1)")
                : "https://www.xvideos.com/?k=\(enc(query))&p=\(page)"
            return htmlVideos(url, "XVideos", "xvideos", #"href="(/video[^"]+)"[\s\S]{0,900}?data-src="(https://[^"]+)""#, "https://www.xvideos.com", daily ? desktopUA : mobileUA)
        case "xnxx":
            let extra = page == 0 ? "" : "/\(page)"
            let url = daily ? "https://www.xnxx.com/todays-selection\(extra)" : "https://www.xnxx.com/search/\(enc(query))\(extra)"
            return htmlVideos(url, "XNXX", "xnxx", #"href="(/video-[^"]+)"[\s\S]{0,900}?data-src="(https://[^"]+)""#, "https://www.xnxx.com", daily ? desktopUA : mobileUA, cap: 48)
        case "xhamster":
            let url = daily ? (page == 0 ? "https://xhamster.com/best/daily" : "https://xhamster.com/best/daily/\(page + 1)")
                : "https://xhamster.com/search/\(enc(query))\(page == 0 ? "" : "?page=\(page + 1)")"
            return htmlVideos(url, "xHamster", "xhamster", #"href="(https://xhamster\.com/videos/[^"]+)"[^>]*>.*?(?:src|data-src)="(https://[^"]+)""#, "", daily ? desktopUA : mobileUA)
        case "xxxbunker":
            let extra = page > 0 ? "/\(page + 1)" : ""
            let url = daily ? "https://xxxbunker.com/\(extra.trimmingCharacters(in: CharacterSet(charactersIn: "/")))" : "https://xxxbunker.com/search/\(enc(query).replacingOccurrences(of: "%20", with: "+"))\(extra)"
            let body = fetch(url, ua: daily ? desktopUA : mobileUA)
            var items: [[String: String]] = []
            for m in matches(#"(?:src|data-src)="https://thumbs\.xxxbunker\.com/(\d+)\.jpg"[^>]*alt="([^"]*)""#, body) where items.count < 40 {
                let id = m[1]
                items.append(item("XXXBunker", "xxxbunker", m[safe: 2], "https://xxxbunker.com/\(id)", "https://thumbs.xxxbunker.com/\(id).jpg", "", ""))
            }
            return fillDurations(items, body)
        case "tnaflix":
            let url = daily ? (page > 0 ? "https://www.tnaflix.com/?page=\(page + 1)" : "https://www.tnaflix.com/")
                : "https://www.tnaflix.com/search.php?what=\(enc(query))\(page > 0 ? "&page=\(page + 1)" : "")"
            let body = fetch(url, ua: daily ? desktopUA : mobileUA)
            var items: [[String: String]] = []
            for chunk in matches(#"(<div data-vid="\d+"[\s\S]{0,3000}?</div>\s*</div>)"#, body) where items.count < 40 {
                let href = matches(#"href="(https://www\.tnaflix\.com/[^"]+/video\d+)""#, chunk[0]).first?[safe: 1] ?? ""
                if href.isEmpty { continue }
                let thumb = matches(#"(?:data-src|src)="(https://(?:cdnl|img)\.tnaflix\.com/[^"]+\.jpg)""#, chunk[0]).first?[safe: 1] ?? ""
                let title = href.replacingOccurrences(of: #"/video\d+$"#, with: "", options: .regularExpression).split(separator: "/").last.map(String.init)?.replacingOccurrences(of: "-", with: " ") ?? ""
                items.append(item("TNAflix", "tnaflix", title, href, cleanThumb(thumb), "", ""))
            }
            return fillDurations(items, body)
        case "drtuber":
            let url = daily ? (page == 0 ? "https://www.drtuber.com/" : "https://www.drtuber.com/latest-updates/\(page + 1)")
                : "https://www.drtuber.com/search/videos/\(enc(query))\(page > 0 ? "/\(page + 1)" : "")"
            return htmlVideos(url, "DrTuber", "drtuber", #"href="(/video/\d+/[^"]+)"[^>]*>\s*<img[^>]+src="(https://[^"]+)""#, "https://www.drtuber.com", daily ? desktopUA : mobileUA)
        case "pornone":
            let url = daily ? (page == 0 ? "https://www.pornone.com/" : "https://www.pornone.com/\(page + 1)/")
                : "https://www.pornone.com/search\(page > 0 ? "/\(page + 1)" : "")/?q=\(enc(query))"
            let body = fetch(url, ua: daily ? desktopUA : mobileUA)
            var thumbs: [String: String] = [:]
            for m in matches(#"(https://th-eu\d+\.pornone\.com/t/\d+/(\d+)/[^"\s]+)"#, body) {
                thumbs[m[2]] = cleanThumb(m[1])
            }
            var items: [[String: String]] = []
            var seen = Set<String>()
            for m in matches(#"href="(https://(?:www\.)?pornone\.com/[^"]+/(\d+)/)""#, body) where items.count < 40 {
                let pageUrl = m[1]
                if seen.contains(pageUrl) { continue }
                seen.insert(pageUrl)
                let title = pageUrl.trimmingCharacters(in: CharacterSet(charactersIn: "/")).split(separator: "/").dropLast().last.map(String.init)?.replacingOccurrences(of: "-", with: " ") ?? ""
                items.append(item("PornOne", "pornone", title, pageUrl, thumbs[m[2]] ?? "", "", ""))
            }
            return fillDurations(items, body)
        case "okxxx":
            let url = daily ? (page == 0 ? "https://ok.xxx/" : "https://ok.xxx/latest-updates/\(page + 1)/")
                : "https://ok.xxx/search/\(enc(query))/\(page > 0 ? "?from_videos=\(page + 1)" : "")"
            let body = fetch(url, ua: daily ? desktopUA : mobileUA)
            var items: [[String: String]] = []
            for m in matches(#"href="(/video/\d+/)"[^>]*title="([^"]*)"[\s\S]{0,700}?data-original="(https://[^"]+)""#, body) where items.count < 40 {
                items.append(item("OK.xxx", "okxxx", m[safe: 2], "https://ok.xxx\(m[1])", cleanThumb(m[safe: 3] ?? ""), "", ""))
            }
            return fillDurations(items, body)
        case "porn00":
            let url = daily ? (page == 0 ? "https://www.porn00.org/latest/" : "https://www.porn00.org/latest/\(page + 1)/")
                : "https://www.porn00.org/q/\(enc(query))/\(page > 0 ? "\(page + 1)/" : "")"
            let body = fetch(url, ua: daily ? desktopUA : mobileUA)
            var items: [[String: String]] = []
            for m in matches(#"href="(https://www.porn00.org/video/[^"]+)"[^>]*title="([^"]*)"[\s\S]{0,600}?data-original="(https://[^"]+)""#, body) where items.count < 40 {
                items.append(item("Porn00", "porn00", m[safe: 2], m[1], cleanThumb(m[safe: 3] ?? ""), "", ""))
            }
            return fillDurations(items, body)
        case "xxxfiles":
            let url = daily ? (page == 0 ? "https://www.xxxfiles.com/" : "https://www.xxxfiles.com/page/\(page + 1)/")
                : "https://www.xxxfiles.com/?s=\(enc(query))\(page > 0 ? "&page=\(page + 1)" : "")"
            return htmlVideos(url, "XXXFiles", "xxxfiles", #"href="(https://www.xxxfiles.com/videos/\d+/[^"]+)"[\s\S]{0,500}?src="(https://img.xxxfiles.com/[^"]+)""#, "", daily ? desktopUA : mobileUA)
        case "xmoviesforyou":
            let url = daily ? (page == 0 ? "https://xmoviesforyou.com/" : "https://xmoviesforyou.com/page/\(page + 1)/")
                : "https://xmoviesforyou.com/?s=\(enc(query))\(page > 0 ? "&paged=\(page + 1)" : "")"
            return htmlVideos(url, "XMoviesForYou", "xmoviesforyou", #"href="(/[a-z0-9-]+)"[^>]*>[\s\S]{0,500}?src="(https://xmoviescdn\.online/[^"]+)""#, "https://xmoviesforyou.com", daily ? desktopUA : mobileUA)
        case "whoreshub":
            let extra = page > 0 ? "?from_videos=\(page + 1)" : ""
            let url = daily ? (page == 0 ? "https://www.whoreshub.com/" : "https://www.whoreshub.com/latest-updates/\(page + 1)/")
                : "https://www.whoreshub.com/search/\(enc(query))/\(extra)"
            let body = fetch(url, ua: daily ? desktopUA : mobileUA)
            var items: [[String: String]] = []
            for m in matches(#"href="(https://www.whoreshub.com/videos/(\d+)/[^"]+)""#, body) where items.count < 40 {
                let num = Int(m[2]) ?? 0
                let bucket = (num / 1000) * 1000
                let title = m[1].trimmingCharacters(in: CharacterSet(charactersIn: "/")).split(separator: "/").last.map(String.init)?.replacingOccurrences(of: "-", with: " ") ?? ""
                let thumb = "https://www.whoreshub.com/contents/videos_screenshots/\(bucket)/\(num)/320x180/1.jpg"
                items.append(item("WhoresHub", "whoreshub", title, m[1], thumb, "", ""))
            }
            return fillDurations(items, body)
        case "yespornvip":
            let url = daily ? (page == 0 ? "https://yespornvip.com/" : "https://yespornvip.com/page/\(page + 1)/")
                : "https://yespornvip.com/?s=\(enc(query))\(page > 0 ? "&paged=\(page + 1)" : "")"
            return htmlVideos(url, "YesPornVIP", "yespornvip", #"href="(https://yespornvip.com/[a-z0-9-]+/)"[\s\S]{0,800}?(?:data-src|src)="(https://yespornvip.com/wp-content/uploads/thumbsx/[^"]+)""#, "", daily ? desktopUA : mobileUA)
        case "justporn":
            let url = daily ? (page == 0 ? "https://www.justporn.to/" : "https://www.justporn.to/page/\(page + 1)/")
                : "https://www.justporn.to/search/\(enc(query))/\(page > 0 ? "page/\(page + 1)/" : "")"
            return htmlVideos(url, "JustPorn", "justporn", #"href="(https://(?:www\.)?justporn.to/[a-z0-9-]+/)"[\s\S]{0,700}?src="(https://justporn.to/cover_upload/[^"]+)""#, "", daily ? desktopUA : mobileUA)
        default:
            return []
        }
    }

    private func htmlVideos(_ url: String, _ provider: String, _ source: String, _ pattern: String, _ prefix: String, _ ua: String, cap: Int = 40) -> [[String: String]] {
        let body = fetch(url, ua: ua)
        var items: [[String: String]] = []
        var seen = Set<String>()
        for m in matches(pattern, body) where items.count < cap {
            let path = m[1]
            let thumb = m[safe: 2] ?? ""
            let pageUrl = path.hasPrefix("http") ? String(path.split(separator: "?").first ?? Substring(path)) : prefix + path
            if seen.contains(pageUrl) || cleanThumb(thumb).isEmpty { continue }
            seen.insert(pageUrl)
            let title = pageUrl.split(separator: "/").last.map(String.init)?.replacingOccurrences(of: "-", with: " ").replacingOccurrences(of: "_", with: " ") ?? ""
            items.append(item(provider, source, title, pageUrl, cleanThumb(thumb), "", ""))
        }
        return fillDurations(items, body)
    }

    private func jsonVideos(_ url: String, provider: String, source: String, list: String, map: ([String: Any]) -> [String: String]) -> [[String: String]] {
        let body = fetch(url)
        guard let data = body.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let rows = obj[list] as? [Any] else { return [] }
        return rows.compactMap { row in
            guard let dict = row as? [String: Any] else { return nil }
            return map(dict)
        }
    }

    private func item(_ provider: String, _ source: String, _ title: String?, _ page: String?, _ thumb: String?, _ embed: String?, _ duration: String?) -> [String: String] {
        let pageUrl = page ?? ""
        let id = source + "-" + sha1(pageUrl.isEmpty ? (title ?? "") : pageUrl).prefix(16)
        return [
            "id": String(id),
            "provider": provider,
            "source": source,
            "title": String((title ?? "").prefix(180)),
            "page": pageUrl,
            "url": pageUrl,
            "thumb": thumb ?? "",
            "embed": embed ?? "",
            "duration": cleanDuration(duration ?? "")
        ]
    }

    private func rank(_ items: [[String: String]], query: String, tags: [String]) -> [[String: String]] {
        if !tags.isEmpty {
            let scored = items.map { item -> (Int, Int, [String: String]) in
                let hits = tags.reduce(0) { $0 + (tagMatched(item, $1) ? 1 : 0) }
                return (hits, relevance(item, terms(for: tags.joined(separator: " "))), item)
            }.sorted { $0.0 == $1.0 ? $0.1 > $1.1 : $0.0 > $1.0 }
            let total = tags.count
            let full = scored.filter { $0.0 >= total }.map { $0.2 }
            let almost = scored.filter { $0.0 >= max(1, total - 1) }.map { $0.2 }
            let some = scored.filter { $0.0 > 0 }.map { $0.2 }
            if full.count >= 6 { return full }
            if almost.count >= 6 { return almost }
            return some
        }
        let tokens = distinctive(query)
        let needed = max(1, (tokens.count + 1) / 2)
        let scored = items.map { item -> (Int, Int, [String: String]) in
            let text = itemText(item)
            let hits = tokens.reduce(0) { $0 + (tokenIn( $1, text) ? 1 : 0) }
            return (hits, relevance(item, terms(for: query)), item)
        }.sorted { $0.0 == $1.0 ? $0.1 > $1.1 : $0.0 > $1.0 }
        let strong = scored.filter { $0.0 >= needed || $0.1 >= 8 }.map { $0.2 }
        return strong.isEmpty ? scored.filter { $0.0 > 0 || $0.1 > 0 }.map { $0.2 } : strong
    }

    private func tagMatched(_ item: [String: String], _ tag: String) -> Bool {
        let text = itemText(item)
        let tokens = distinctive(tag)
        if tokens.isEmpty { return relevance(item, terms(for: tag)) >= 6 }
        return tokens.contains { tokenIn($0, text) }
    }

    private func itemText(_ item: [String: String]) -> (String, String, String) {
        let title = norm(item["title"] ?? "")
        let page = norm((item["page"] ?? "") + " " + (item["url"] ?? ""))
        return (title, page, title.replacingOccurrences(of: " ", with: ""))
    }

    private func tokenIn(_ token: String, _ text: (String, String, String)) -> Bool {
        let (title, page, compact) = text
        if token == "ai" { return title.range(of: #"\bai\b"#, options: .regularExpression) != nil || page.range(of: #"\bai\b"#, options: .regularExpression) != nil }
        if title.range(of: "\\b\(NSRegularExpression.escapedPattern(for: token))\\b", options: .regularExpression) != nil { return true }
        if token.count >= 4 && compact.contains(token) { return true }
        return page.range(of: "\\b\(NSRegularExpression.escapedPattern(for: token))\\b", options: .regularExpression) != nil
    }

    private func relevance(_ item: [String: String], _ terms: [String]) -> Int {
        let (title, page, compact) = itemText(item)
        if terms.isEmpty { return 1 }
        var score = 0
        for term in terms {
            if term.contains(" ") {
                if title.contains(term) { score += 12 }
                else if page.contains(term) { score += 4 }
                continue
            }
            if tokenIn(term, (title, page, compact)) {
                if title.range(of: "\\b\(NSRegularExpression.escapedPattern(for: term))\\b", options: .regularExpression) != nil { score += 6 }
                else { score += 2 }
            }
        }
        return score
    }

    private func terms(for query: String) -> [String] {
        var out: [String] = []
        var seen = Set<String>()
        let phrase = expand(query).lowercased()
        for raw in [phrase, query.lowercased()] {
            let normed = norm(raw)
            if !normed.isEmpty { appendTerm(normed, &out, &seen) }
            for token in normed.split(separator: " ").map(String.init) where !stop.contains(token) && (token.count >= 2 || token == "ai") {
                appendTerm(token, &out, &seen)
            }
        }
        return out
    }

    private func distinctive(_ query: String) -> [String] {
        norm(expand(query)).split(separator: " ").map(String.init).filter { !stop.contains($0) && ($0.count >= 2 || $0 == "ai") }
    }

    private func combine(_ tags: [String]) -> String {
        var words: [String] = []
        var seen = Set<String>()
        for tag in tags {
            for word in expand(tag).split(separator: " ").map(String.init) {
                let key = word.lowercased()
                if stop.contains(key) || seen.contains(key) { continue }
                seen.insert(key)
                words.append(word)
                if words.count >= 6 { return words.joined(separator: " ") }
            }
        }
        return words.joined(separator: " ")
    }

    private func expand(_ query: String) -> String {
        if isDaily(query) { return query }
        let key = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            .replacingOccurrences(of: #"[\s_]+"#, with: " ", options: .regularExpression)
        return phrases[key] ?? query.trimmingCharacters(in: .whitespaces)
    }

    private func allowed(_ row: [String: String]) -> Bool {
        let blob = [row["title"], row["page"], row["url"]].compactMap { $0 }.joined(separator: " ")
        if blocked(blob) { return false }
        return !hostBlocked(row["page"] ?? "") && !hostBlocked(row["url"] ?? "")
    }

    private func blocked(_ query: String) -> Bool {
        query.range(of: #"\b(child|children|kid|kids|toddler|infant|baby|babies|minor|minors|underage|under[\s-]?age|preteen|pre[\s-]?teen|loli|lolita|shota|pedo|paedo|jailbait|young[\s-]?girl|little[\s-]?girl|(1[0-7]|[0-9])\s*(yo|yr|years?\s*old)|leak|leaked|leaks|stolen|hacked|fappening|celebgate|revenge\s*porn|non[\s-]?consensual|without\s+consent|no\s+consent|hidden\s*cam|spy\s*cam|voyeur|creepshot|upskirt|downblouse|passed\s+out|unconscious|drugged|sleeping\s+nude|rape|raped|forced|blackmail|deepnude|undress)\b"#, options: [.regularExpression, .caseInsensitive]) != nil
    }

    private func hostBlocked(_ url: String) -> Bool {
        guard let host = URL(string: url)?.host?.lowercased() else { return !url.isEmpty }
        let bits = ["leak", "leaked", "thothub", "fappening", "celebgate", "nudel", "coomer", "kemono", "simpcity", "fapello", "cyberdrop"]
        return bits.contains { host.contains($0) }
    }

    private func fillDurations(_ items: [[String: String]], _ body: String) -> [[String: String]] {
        items.map { row in
            var copy = row
            let current = cleanDuration(row["duration"] ?? "")
            if !current.isEmpty {
                copy["duration"] = current
                return copy
            }
            let needle = row["thumb"]?.isEmpty == false ? row["thumb"]! : (row["page"] ?? "")
            guard !needle.isEmpty, let range = body.range(of: String(needle.prefix(90))) else { return copy }
            let start = body.index(range.lowerBound, offsetBy: -400, limitedBy: body.startIndex) ?? body.startIndex
            let end = body.index(range.upperBound, offsetBy: 2800, limitedBy: body.endIndex) ?? body.endIndex
            copy["duration"] = pickDuration(String(body[start..<end]))
            return copy
        }
    }

    private func pickDuration(_ chunk: String) -> String {
        if let m = matches(#"(?:class|id)="[^"]*(?:duration|runtime|video-time|video-duration|length)[^"]*"[^>]*>([^<]{1,32})"#, chunk).first, let got = optionalClean(m[safe: 1] ?? "") { return got }
        let times = matches(#"(?<!\d)(\d{1,2}:\d{2}(?::\d{2})?)(?!\d)"#, chunk).compactMap { optionalClean($0[1]) }
        if let last = times.last { return last }
        if let m = matches(#"(\d{1,3})\s*(?:min|mins|minutes)\b"#, chunk).first { return cleanDuration(m[0]) }
        return ""
    }

    private func optionalClean(_ raw: String) -> String? {
        let got = cleanDuration(raw)
        return got.isEmpty ? nil : got
    }

    private func cleanDuration(_ raw: String) -> String {
        var text = raw.replacingOccurrences(of: #"<[^>]+>"#, with: " ", options: .regularExpression)
        text = text.replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression).trimmingCharacters(in: .whitespaces)
        if text.isEmpty { return "" }
        if text.range(of: #"^\d{1,5}$"#, options: .regularExpression) != nil, let total = Int(text), total > 0, total <= 12 * 3600 {
            let h = total / 3600, m = (total % 3600) / 60, s = total % 60
            return h > 0 ? String(format: "%d:%02d:%02d", h, m, s) : String(format: "%d:%02d", m, s)
        }
        if let m = matches(#"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})"#, text).first {
            let second = Int(m[safe: 3] ?? "0") ?? 0
            if second > 59 { return "" }
            if let hour = m[safe: 1], !hour.isEmpty {
                return "\(Int(hour) ?? 0):\(String(format: "%02d", Int(m[2]) ?? 0)):\(String(format: "%02d", second))"
            }
            return "\(Int(m[2]) ?? 0):\(String(format: "%02d", second))"
        }
        if let m = matches(#"(\d{1,3})\s*(?:min|mins|minutes)\b"#, text).first {
            return "\(Int(m[1]) ?? 0):00"
        }
        return ""
    }

    private func cleanThumb(_ url: String) -> String {
        var value = url
        if value.hasPrefix("//") { value = "https:" + value }
        let low = value.lowercased()
        if ["blank.gif", "lightbox-blank", "placeholder", "pixel.gif", "1x1"].contains(where: { low.contains($0) }) { return "" }
        return value
    }

    private func interleave(_ items: [[String: String]]) -> [[String: String]] {
        var buckets: [String: [[String: String]]] = [:]
        var order: [String] = []
        for row in items {
            let src = row["source"] ?? ""
            if buckets[src] == nil { order.append(src); buckets[src] = [] }
            buckets[src]?.append(row)
        }
        var out: [[String: String]] = []
        var more = true
        while more {
            more = false
            for src in order {
                if !(buckets[src] ?? []).isEmpty {
                    out.append(buckets[src]!.removeFirst())
                    more = true
                }
            }
        }
        return out
    }

    private func fetch(_ url: String, ua: String? = nil, referer: String? = nil) -> String {
        let got = fetchBytes(url, accept: "text/html,application/json;q=0.9,*/*;q=0.8", referer: referer, ua: ua)
        return String(data: got.data, encoding: .utf8) ?? ""
    }

    private func fetchBytes(_ url: String, accept: String, referer: String? = nil, ua: String? = nil) -> (data: Data, mime: String, status: Int) {
        guard let remote = URL(string: url) else { return (Data(), "", 400) }
        var req = URLRequest(url: remote, timeoutInterval: 12)
        req.setValue(ua ?? desktopUA, forHTTPHeaderField: "User-Agent")
        req.setValue(accept, forHTTPHeaderField: "Accept")
        req.setValue("en-US,en;q=0.9", forHTTPHeaderField: "Accept-Language")
        if let referer, referer.hasPrefix("http") {
            req.setValue(referer, forHTTPHeaderField: "Referer")
        } else if let host = remote.host {
            req.setValue("https://\(host)/", forHTTPHeaderField: "Referer")
        }
        let sem = DispatchSemaphore(value: 0)
        var data = Data()
        var mime = ""
        var status = 0
        URLSession.shared.dataTask(with: req) { body, response, _ in
            data = body ?? Data()
            if let http = response as? HTTPURLResponse {
                status = http.statusCode
                mime = http.value(forHTTPHeaderField: "Content-Type") ?? ""
            }
            sem.signal()
        }.resume()
        _ = sem.wait(timeout: .now() + 14)
        return (data, mime, status)
    }

    private func matches(_ pattern: String, _ text: String) -> [[String]] {
        guard let re = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else { return [] }
        let range = NSRange(text.startIndex..., in: text)
        return re.matches(in: text, range: range).map { m in
            (0..<m.numberOfRanges).map { i in
                let r = m.range(at: i)
                guard r.location != NSNotFound, let swift = Range(r, in: text) else { return "" }
                return String(text[swift])
            }
        }
    }

    private func loadDaily(source: String, page: Int) -> [String: Any]? {
        let file = dailyFile(source: source, page: page)
        guard let data = try? Data(contentsOf: file),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              obj["date"] as? String == today(),
              let items = obj["items"] as? [Any], !items.isEmpty else { return nil }
        return obj
    }

    private func saveDaily(source: String, page: Int, payload: [String: Any]) {
        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload) else { return }
        try? data.write(to: dailyFile(source: source, page: page), options: .atomic)
    }

    private func dailyFile(source: String, page: Int) -> URL {
        let safe = source.lowercased().replacingOccurrences(of: "[^a-z0-9]+", with: "-", options: .regularExpression)
        return FileManager.default.temporaryDirectory.appendingPathComponent("gitvidx-daily-\(today())-\(safe)-\(page).json")
    }

    private func json(_ payload: [String: Any], statusHint: Int = 200) -> Data {
        (try? JSONSerialization.data(withJSONObject: payload)) ?? Data("{\"items\":[]}".utf8)
    }

    private func queryItem(_ url: URL, _ name: String) -> String? {
        URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == name })?.value
    }

    private func isDaily(_ query: String) -> Bool {
        query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == dailyQ
    }

    private func today() -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: Date())
    }

    private func text(_ value: Any?) -> String? {
        if let s = value as? String { return s }
        if let n = value as? NSNumber { return n.stringValue }
        return nil
    }

    private func enc(_ value: String) -> String {
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: ":/?#[]@!$&'()*+,;=")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }

    private func norm(_ value: String) -> String {
        value.lowercased().replacingOccurrences(of: "[^a-z0-9]+", with: " ", options: .regularExpression).trimmingCharacters(in: .whitespaces)
    }

    private func appendTerm(_ term: String, _ out: inout [String], _ seen: inout Set<String>) {
        if seen.insert(term).inserted { out.append(term) }
    }

    private func sha1(_ value: String) -> String {
        Insecure.SHA1.hash(data: Data(value.utf8)).map { String(format: "%02x", $0) }.joined()
    }
}

private extension Array where Element == String {
    subscript(safe index: Int) -> String? {
        indices.contains(index) ? self[index] : nil
    }
}

import UIKit
import WebKit

final class ViewController: UIViewController, WKScriptMessageHandler {
    private var webView: WKWebView!
    private let scheme = AppSchemeHandler()

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 16 / 255, green: 8 / 255, blue: 13 / 255, alpha: 1)

        let inject = WKUserScript(
            source: """
            window.GitImgX = window.GitImgX || {
              openUrl: function(url) {
                window.webkit.messageHandlers.gitvidx.postMessage({ action: "openUrl", url: url });
              }
            };
            """,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        )

        let config = WKWebViewConfiguration()
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.userContentController.addUserScript(inject)
        config.userContentController.add(self, name: "gitvidx")
        config.websiteDataStore = .default()
        config.setURLSchemeHandler(scheme, forURLScheme: "gitvidx")

        let webView = WKWebView(frame: view.bounds, configuration: config)
        webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        webView.isOpaque = false
        webView.backgroundColor = view.backgroundColor
        webView.scrollView.backgroundColor = view.backgroundColor
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.bounces = false
        webView.customUserAgent = ((webView.value(forKey: "userAgent") as? String) ?? "") + " GitVidX/3.2"
        view.addSubview(webView)
        self.webView = webView

        webView.load(URLRequest(url: URL(string: "gitvidx://local/index.html")!))
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "gitvidx", let body = message.body as? [String: Any] else { return }
        if body["action"] as? String == "openUrl", let urlString = body["url"] as? String,
           let url = URL(string: urlString), url.scheme == "https" || url.scheme == "http" {
            UIApplication.shared.open(url)
        }
    }
}

final class AppSchemeHandler: NSObject, WKURLSchemeHandler {
    private let engine = SearchEngine()
    private let lock = NSLock()
    private var stopped = Set<ObjectIdentifier>()

    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        let request = urlSchemeTask.request
        let id = ObjectIdentifier(urlSchemeTask)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.handle(request, task: urlSchemeTask, id: id)
        }
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {
        lock.lock()
        stopped.insert(ObjectIdentifier(urlSchemeTask))
        lock.unlock()
    }

    private func isStopped(_ id: ObjectIdentifier) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return stopped.contains(id)
    }

    private func handle(_ request: URLRequest, task: WKURLSchemeTask, id: ObjectIdentifier) {
        guard let url = request.url else { return }
        let path = url.path.isEmpty ? "/index.html" : url.path
        if path == "/api/search" {
            let data = engine.search(url: url)
            finish(task, id: id, data: data, mime: "application/json", status: 200)
            return
        }
        if path == "/api/img" {
            let result = engine.fetchImage(url: url)
            finish(task, id: id, data: result.data, mime: result.mime, status: result.status)
            return
        }
        serveFile(path, task: task, id: id)
    }

    private func serveFile(_ path: String, task: WKURLSchemeTask, id: ObjectIdentifier) {
        let relative = path.hasPrefix("/") ? String(path.dropFirst()) : path
        let clean = relative.isEmpty ? "index.html" : relative
        guard let file = Bundle.main.url(forResource: (clean as NSString).deletingPathExtension,
                                         withExtension: (clean as NSString).pathExtension.isEmpty ? nil : (clean as NSString).pathExtension,
                                         subdirectory: wwwSubdir(clean))
                ?? Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "www") else {
            finish(task, id: id, data: Data("missing".utf8), mime: "text/plain", status: 404)
            return
        }
        let data = (try? Data(contentsOf: file)) ?? Data()
        finish(task, id: id, data: data, mime: mime(for: file.pathExtension), status: 200)
    }

    private func wwwSubdir(_ clean: String) -> String {
        let dir = (clean as NSString).deletingLastPathComponent
        return dir.isEmpty ? "www" : "www/\(dir)"
    }

    private func mime(for ext: String) -> String {
        switch ext.lowercased() {
        case "html": return "text/html"
        case "css": return "text/css"
        case "js": return "text/javascript"
        case "json": return "application/json"
        case "png": return "image/png"
        case "jpg", "jpeg": return "image/jpeg"
        case "svg": return "image/svg+xml"
        case "ttf": return "font/ttf"
        case "woff", "woff2": return "font/woff"
        default: return "application/octet-stream"
        }
    }

    private func finish(_ task: WKURLSchemeTask, id: ObjectIdentifier, data: Data, mime: String, status: Int) {
        if isStopped(id) { return }
        let response = HTTPURLResponse(
            url: task.request.url ?? URL(string: "gitvidx://local/")!,
            statusCode: status,
            httpVersion: "HTTP/1.1",
            headerFields: [
                "Content-Type": mime,
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-store",
                "Content-Length": "\(data.count)"
            ]
        )!
        DispatchQueue.main.async {
            if self.isStopped(id) { return }
            task.didReceive(response)
            task.didReceive(data)
            task.didFinish()
        }
    }
}

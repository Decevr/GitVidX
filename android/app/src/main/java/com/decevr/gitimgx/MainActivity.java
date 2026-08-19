package com.decevr.gitimgx;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.FrameLayout;

import androidx.activity.OnBackPressedCallback;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewClientCompat;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends AppCompatActivity {
    private final SearchEngine search = new SearchEngine();
    private WebView webView;
    private FrameLayout root;
    private View customView;
    private WebChromeClient.CustomViewCallback customCallback;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        root = new FrameLayout(this);
        webView = new WebView(this);
        webView.setBackgroundColor(0xFF10080D);
        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));
        setContentView(root);

        WebViewAssetLoader assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setUserAgentString(settings.getUserAgentString() + " GitVidX/1.3");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onShowCustomView(View view, CustomViewCallback callback) {
                if (customView != null) {
                    callback.onCustomViewHidden();
                    return;
                }
                customView = view;
                customCallback = callback;
                webView.setVisibility(View.GONE);
                root.addView(view, new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                ));
                getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
            }

            @Override
            public void onHideCustomView() {
                if (customView == null) {
                    return;
                }
                root.removeView(customView);
                customView = null;
                webView.setVisibility(View.VISIBLE);
                if (customCallback != null) {
                    customCallback.onCustomViewHidden();
                    customCallback = null;
                }
                getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
            }
        });
        webView.addJavascriptInterface(new Bridge(), "GitImgX");

        webView.setWebViewClient(new WebViewClientCompat() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String path = uri.getPath();
                if ("/api/search".equals(path)) {
                    return handleSearch(uri);
                }
                if ("/api/img".equals(path)) {
                    return handleImage(uri);
                }
                return assetLoader.shouldInterceptRequest(uri);
            }
        });
        webView.loadUrl("https://appassets.androidplatform.net/assets/index.html");

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (customView != null && webView.getWebChromeClient() != null) {
                    webView.getWebChromeClient().onHideCustomView();
                    return;
                }
                webView.evaluateJavascript(
                        "(function(){return window.DE_onBack ? String(window.DE_onBack()) : 'false';})()",
                        value -> {
                            if ("\"true\"".equals(value) || "true".equals(value)) {
                                return;
                            }
                            finish();
                        }
                );
            }
        });
    }

    private WebResourceResponse handleSearch(Uri uri) {
        String query = uri.getQueryParameter("q");
        String source = uri.getQueryParameter("source");
        if (source == null || source.isEmpty()) {
            source = "all";
        }
        int page = 0;
        try {
            page = Math.max(0, Integer.parseInt(uri.getQueryParameter("page")));
        } catch (Exception ignored) {
            page = 0;
        }
        String blocked = search.blockedQuery(query == null ? "" : query);
        if (blocked != null) {
            return json(400, "{\"error\":" + JSONObject.quote(blocked) + ",\"items\":[]}");
        }
        boolean refresh = "1".equals(uri.getQueryParameter("refresh"));
        try {
            JSONObject payload = search.search(query == null ? "" : query, source, page, refresh, uri.getQueryParameter("tags"));
            return json(200, payload.toString());
        } catch (Exception error) {
            String message = error.getMessage() == null ? "Search failed" : error.getMessage();
            return json(502, "{\"error\":" + JSONObject.quote(message) + ",\"items\":[]}");
        }
    }

    private WebResourceResponse handleImage(Uri uri) {
        String target = uri.getQueryParameter("url");
        try {
            SearchEngine.ImageResult image = search.fetchImage(target, uri.getQueryParameter("ref"));
            Map<String, String> headers = new HashMap<>();
            headers.put("Access-Control-Allow-Origin", "*");
            headers.put("Cache-Control", "no-store");
            return new WebResourceResponse(
                    image.contentType,
                    null,
                    200,
                    "OK",
                    headers,
                    new ByteArrayInputStream(image.body)
            );
        } catch (Exception error) {
            return json(502, "{\"error\":\"Image fetch failed\"}");
        }
    }

    public class Bridge {
        @JavascriptInterface
        public void openUrl(@NonNull String url) {
            if (url == null || !(url.startsWith("https://") || url.startsWith("http://"))) {
                return;
            }
            runOnUiThread(() -> startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))));
        }
    }

    private WebResourceResponse json(int code, String body) {
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", "application/json; charset=utf-8");
        headers.put("Access-Control-Allow-Origin", "*");
        headers.put("Cache-Control", "no-store");
        String reason = code >= 400 ? "Error" : "OK";
        return new WebResourceResponse(
                "application/json",
                "utf-8",
                code,
                reason,
                headers,
                new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8))
        );
    }
}

# GitVidX

A phone-friendly porn video search engine. It looks across public tube sites and shows the results in one place, with categories and filters.

18+ only. Videos must be legal and consensual. It does not search leak dumps, stolen content, hidden-camera material, or anything involving minors.

## Use on your phone (Add to Home Screen)

Open this link in Safari (iPhone) or Chrome (Android):

**https://decevr.github.io/GitVidX/**

Then:

- **iPhone:** tap Share → **Add to Home Screen**
- **Android:** tap the menu → **Add to Home screen** / **Install app**

You get the GitVidX icon and it opens full-screen. No PC server needed for this web version.

## Install on your phone

The standalone Android app is `GitVidX.apk` in this folder.

1. Send `GitVidX.apk` to your phone (Phone Link, USB, Drive, or email).
2. Open the file on the phone.
3. If Samsung blocks it, tap **Settings** and allow installs from that app.
4. Install. The icon is **GitVidX**.

The phone app searches on its own. You do not need this PC running.

To rebuild the Android app after changes, run `build-apk.bat`.

## Install on iPhone

The iPhone project is in `ios/`, same kind of WebView wrapper as the other iOS app. It cannot be built on Windows.

1. Run `python ios/copy_web.py` and `python ios/make_ios_assets.py`.
2. Copy the project to a Mac and open `ios/GitVidX.xcodeproj` in Xcode.
3. Sign it with your Apple ID and run it on a plugged-in iPhone.

See `ios/README.md` for the full steps. Apple will not list this on the App Store.

## Try it on this PC

Double-click `start.bat`, then open http://127.0.0.1:8767

On the phone, while the PC is running and both are on the same Wi-Fi: use the Phone address printed in the window.

## What it does

- Age gate before any search
- Categories: amateur, MILF, lesbian, blonde, and more
- Sites: All, Pornhub, XVideos, xHamster, XNXX, YouPorn, RedTube, Eporner
- Tap a video to play the embed when the site allows it, or open it on the source site
- Heart / Save keeps videos on this device only

This is a search viewer for public, consensual adult videos. It is not a downloader for stolen or non-consensual content.

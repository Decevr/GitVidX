# GitVidX for iPhone

This is a native iOS wrapper, the same style as the other phone app. It cannot be compiled on Windows.

The iPhone app includes the same local search engine as Android. It does not need the PC Python server.

## On a Mac

1. Copy this whole `gitImgX` folder to a Mac, or at least the `ios` folder after syncing web files.
2. On the PC first (or on the Mac if Python is there), run:

   ```
   python ios/copy_web.py
   python ios/make_ios_assets.py
   ```

3. Open `ios/GitVidX.xcodeproj` in Xcode.
4. Select your Apple ID under **Signing & Capabilities**.
5. Plug in an iPhone, pick it as the run destination, and tap Run.

For TestFlight or Ad Hoc, use **Product → Archive**.

## What you get

- Same UI as Android: Today, filters, categories, Refresh
- Searches tube sites on the phone
- Age gate, save list, and in-app player when the site allows embeds
- 18+ only, legal/consensual videos only

Apple will not list this on the App Store. Sideload with your Apple ID, or use a developer certificate.

# newbroman.github.io

Root user site. Hosts the `.well-known/assetlinks.json` needed for
the Polski Trener TWA Android app to open without falling back to Chrome.

## Setup
1. Upload all files in this repo to a GitHub repo named exactly `newbroman.github.io`
2. Enable GitHub Pages on the `main` branch
3. Verify: https://newbroman.github.io/.well-known/assetlinks.json

## Getting your SHA-256 fingerprint
In Android Studio, open the Terminal tab and run:
```
keytool -list -v -keystore signing.keystore
```
Enter your keystore password when prompted.
Copy the SHA-256 line and paste it into `.well-known/assetlinks.json`
replacing PASTE_YOUR_SHA256_FINGERPRINT_HERE

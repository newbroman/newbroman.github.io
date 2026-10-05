# newbroman.github.io

Root user site, live at https://newbroman.github.io/

- `index.html` is the app directory: every live app, what it does, and links to it and its source.
  When an app is added, retired or renamed, update its card here.
- `.well-known/assetlinks.json` lets the Polski Trener Android app open full screen
  instead of falling back to Chrome. `_config.yml` makes sure GitHub Pages publishes it.
  The fingerprint must match the app's signing certificate (see the `Polska` repo README).

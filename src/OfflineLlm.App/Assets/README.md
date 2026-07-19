# Assets

- `app.ico` — the app's icon: multi-resolution (16/32/48/64/128/256px), used for the executable icon (`ApplicationIcon` in `OfflineLlm.App.csproj`) and the Start Menu/Desktop shortcuts created by the WiX installer (`installer/Product.wxs` references `$(var.AppIcon)`).
- `logo.png` — the full landscape artwork `app.ico` is cropped from: a black clip-art silhouette of a lighthouse rising left-of-center above a long low building with a stepped roofline, windows cut out as transparent holes.
- `generate_logo.py` — regenerates both of the above from scratch (plain shapes drawn with Pillow, no external image files needed). Run `python generate_logo.py` from this directory after editing it; requires `pip install pillow`.

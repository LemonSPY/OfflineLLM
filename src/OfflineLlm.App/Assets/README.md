# Assets

Add `app.ico` here (multi-resolution .ico, e.g. 16/32/48/256px) before shipping — it's used for:

- the app's executable icon (uncomment `ApplicationIcon` in `OfflineLlm.App.csproj`)
- the Start Menu and Desktop shortcuts created by the WiX installer (`installer/Product.wxs` references `$(var.AppIcon)`)

No icon is checked in yet since it needs real artwork rather than a placeholder.

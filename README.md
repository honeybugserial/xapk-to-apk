# XapkToApk - Standalone Windows Fork

This is a Windows-focused fork of the original **XapkToApk** tool, updated to run fully offline and locally on Windows without needing to install or configure system-wide tools.

This version includes:
- Local tooling (`apktool`, `zipalign`, `apksigner`)
- Auto-handling of `.xapk` extraction, APK part merging, zipalign, and signing
- Optional auto-generated debug keystore if one isn't provided

---

## ✅ Features

- ✔️ Converts `.xapk` files into installable `.apk`
- ✔️ Cleans `AndroidManifest.xml` to remove split requirements
- ✔️ Uses `apktool` to unpack and rebuild the main APK
- ✔️ Zipaligns APK for optimal installation
- ✔️ **Signs automatically** with:
  - Either a user-provided keystore (`xapktoapk.sign.properties`)
  - Or a locally generated debug keystore
- 🧰 **Standalone: no external setup required on Windows**

---

## 🔧 Requirements

- 🪟 **Windows Build**
- 💡 All required tools must exist in the local `tools/` directory:

```
tools/
├── apktool.bat
├── apktool_*.jar
├── zipalign.exe
├── apksigner.bat
└── apksigner.jar
```

- 🧾 Optional: `xapktoapk.sign.properties` to control signing behavior (see below)

---

## 🚀 Usage

Place your `.xapk` file in the same directory as the script, then run:

```bash
python xapktoapk-Local-Win.py "YourApp.xapk"
```

The script will:
1. Extract the `.xapk`
2. Decompile the main APK
3. Clean the manifest
4. Rebuild and zipalign
5. Sign the APK (with debug or user keystore)
6. Save output next to the input file

---

## 🔐 Optional Signing Config

If you'd like to use your own keystore, create a file named:

```
xapktoapk.sign.properties
```

Example contents:

```
sign.enabled=true
sign.keystore.file=tools/my-release-key.keystore
sign.keystore.password=yourKeystorePassword
sign.key.alias=yourKeyAlias
sign.key.password=yourKeyPassword
```

If `sign.enabled` is `true` and this file is present, your keystore will be used.

---

## 📁 Output

On success, a signed, installable APK will be saved to:

```
<CurrentDir>\YourApp.apk
```

---

## 📝 License

This project is a fork of [https://github.com/LuigiVampa92/xapk-to-apk](https://github.com/LuigiVampa92/xapk-to-apk), originally released under the MIT License.


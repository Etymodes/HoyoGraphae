<p align="center">
  <img src="./src/hoyographae/resources/hoyographae-icon.svg" width="184" alt="HoyoGraphae icon">
</p>

<h1 align="center">HoyoGraphae</h1>

<p align="center"><strong>A local workspace for HoYoverse constructed scripts</strong></p>

<p align="center"><a href="./README.md">简体中文</a> · <strong>English</strong></p>

> [!IMPORTANT]
> This project is currently a desktop prototype. The foundations for font browsing and text generation are being implemented; native Martian rendering and constructed-script OCR are not complete. The README distinguishes working features from planned work and does not present generic OCR as a script-specific recognizer.

## One application, four workflows

| Module | Purpose | Current status |
| --- | --- | --- |
| Font library | Collect and filter constructed-script fonts from the games | Latest font sources inherited; desktop app can load local OpenType fonts |
| Glyph browser | Browse a font by character, Unicode value, and glyph | Qt prototype available |
| Text generator | Type for live preview and export a transparent or solid-background PNG | Qt prototype available |
| Image text recognition | Locate and transcribe constructed scripts in screenshots | UI and engine boundary reserved; dedicated models still need training |

Martian is not a conventional font: it is a compositional vector writing system. HoyoGraphae preserves the complete upstream implementation and will port it natively to Qt `QPainter` instead of embedding a browser runtime.

## Local Qt architecture

The first release uses **Python 3.11 + PySide6 6.9+ + Qt Widgets**:

- Qt provides the desktop UI, in-process font loading, screen rendering, and image export;
- fontTools reads cmaps, glyph names, and font metadata;
- `.glyphs` sources are converted with glyphsLib/fontmake only at build time and are never modified at runtime;
- OCR training stays outside the desktop app; future packages will carry only versioned ONNX inference models;
- fonts are loaded for the current process and are not installed into the Windows font directory.

### Run from source (Windows PowerShell)

```powershell
git clone https://github.com/Etymodes/HoyoGraphae.git
Set-Location HoyoGraphae

py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m hoyographae
```

The current development source primarily contains the HoYo fonts as `.glyphs` files. To exercise the desktop prototype, load an already compiled `.ttf` or `.otf` file from the application.

## Upstream resources and pinned versions

HoyoGraphae is a local application built after both @SpeedyOrc-C and @Etymodes contributed to the related resources. The current source snapshots are pinned as follows:

| Source | Branch and commit | Location in this repository |
| --- | --- | --- |
| [HoYo-Glyphs](https://github.com/SpeedyOrc-C/HoYo-Glyphs) | `main@ad0c03ce9792d623c6a6161e5582a01903bd5d97` | Git history and `src/*.glyphs` |
| [Honkai-3rd-II-Martian](https://github.com/SpeedyOrc-C/Honkai-3rd-II-Martian) | `main@89998b86c83e364d970be639917f422b00d6015b` | `upstream/Honkai-3rd-II-Martian/` |

Both upstream projects currently expose `main` as their only public development branch. The exact machine-readable record is in [`upstreams.lock.json`](./upstreams.lock.json). The inherited HoYo-Glyphs fonts are manually reconstructed resources and are **not extracted game files**.

## Roadmap

- **M0 · Desktop foundation:** font loading, glyph grid, live typing preview, PNG export, and an explicit OCR placeholder.
- **M1 · Bundled library:** batch font builds and catalog; variable axes; native Qt Martian rendering with golden-image regression tests.
- **M2 · Local OCR:** begin with one script and manually selected text lines, freeze an evaluation set and publish accuracy, then add automatic text detection.

## Support the developers

<table>
  <tr>
    <td align="center">
      <strong>陈湛明 · WeChat</strong><br><br>
      <img src="./donation-wechat.jpg" width="280" alt="Chen Zhanming's WeChat donation code">
    </td>
    <td align="center">
      <strong>@Etymodes · Zelle</strong><br><br>
      <code>Peterpig123456@gmail.com</code>
    </td>
  </tr>
</table>

Donations are voluntary support. They do not purchase or grant a commercial license to the fonts.

## Licenses and notices

- HoYo-Glyphs font and alphabet resources follow the repository root's [custom non-commercial license](./LICENSE), including requirements for embedding, modifications, and source links.
- The original Martian implementation follows the [MIT License](./upstream/Honkai-3rd-II-Martian/LICENSE), Copyright © 2023 陈湛明.
- A separate license has not yet been selected for original application code; neither upstream license automatically extends to new application code.
- See [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md) for full provenance and third-party notices.

HoyoGraphae is an unofficial fan project and is not affiliated with, sponsored by, or endorsed by HoYoverse or its affiliates. Game and product names belong to their respective owners.

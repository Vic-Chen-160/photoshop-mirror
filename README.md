# photoshop-mirror

**English** · [繁體中文](README.zh-TW.md)

See your Photoshop design on your phone, live, while you work. Every time you edit a layer, the phone updates within a second.

No phone app. No plugin. No account. One command on your Mac and a browser on your phone.

<!-- TODO: demo GIF — Photoshop on the left, phone updating on the right -->
<!-- ![demo](docs/demo.gif) -->

## Why

Adobe shut down Preview CC / Device Preview, Skala Preview is no longer maintained, and the remaining third-party plugins run inside Photoshop's Generator process, where a crash takes the whole thing down.

photoshop-mirror stays outside Photoshop. It uses Photoshop's built-in **Image Assets** export, which rewrites a PNG every time you edit, and serves those PNGs to your phone over Wi-Fi.

- **Pixel-accurate.** The phone shows the PNG Photoshop actually exported. Colors, font weights and 1px lines come out exactly as rendered. A screen stream can't give you that.
- **Several artboards and PSDs at once.** Switch between them from a menu on the phone. Open another PSD and it shows up within 3 seconds.
- **Works with PSDs on a NAS.** It fixes a Generator bug that silently breaks exports from network drives (see [PSDs on a network drive](#psds-on-a-network-drive)).
- **Private by default.** The URL contains a random token, so coworkers on the same Wi-Fi can't browse your unreleased work.
- **Nothing to install besides itself.** It uses the Python that comes with macOS.

## Requirements

- macOS, Photoshop CC (any recent version)
- Python 3. If `python3` asks you to install developer tools, accept, or run `xcode-select --install`
- Mac and phone on the same Wi-Fi

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/Vic-Chen-160/photoshop-mirror/main/install.sh | zsh
```

Or clone the repo and run `./install.sh`. Optional: `brew install qrencode` to get a QR code in Terminal.

## Set up Photoshop (once)

1. **Settings > Plugins**: tick **Enable Generator**.
2. **File > Generate > Image Assets**: tick it. This is a per-document switch, so turn it on in every PSD you want to see.
3. Rename your **artboard** to `preview.png`.

> Use an **artboard**, not a layer group. A group is cropped to its visible pixels, so its size jumps around as you edit. An artboard always exports the full canvas at a constant size.

Artboard naming cheatsheet:

```text
preview.png              PNG at original size
200% preview.png         2× size (sharper on high-density phones)
750x1334 preview.png     exact output size
preview.jpg8             JPG, quality 8
1. home.png              number prefixes control the order on the phone
```

## Use

```sh
psmirror ~/Design/app/home.psd          # one PSD
psmirror a.psd b.psd                    # several PSDs
psmirror ~/Design/app                   # every PSD with Image Assets on, in this folder
psmirror                                # same as last time
```

Tip: type `psmirror ` (with a space), then drag the PSD from Finder into Terminal.

Terminal prints a URL (and a QR code). Open it on your phone and keep it open.

On the phone:

| Control | What it does |
|---|---|
| File name | Pick an artboard / PSD |
| Fit · Full width · 1:1 pixels | Use **Full width** to judge the layout the way it looks in a real app, **1:1** for detail |
| Background | Dark / light / checkerboard for transparency |
| Green dot + time | Connected, and when the last new image arrived |

The page follows your phone's language (English or Traditional Chinese).

## PSDs on a network drive

If your PSDs live on a NAS / SMB share, add `--local`:

```sh
psmirror /Volumes/NAS/project/v3.psd --local
```

**What goes wrong without it:** Generator renders each image into a local temp folder, then `rename()`s it into `<name>-assets/`. `rename()` can't cross filesystems, so every write fails with `EXDEV`. Generator falls back to copying, which races with its own deletes, and eventually its internal state breaks. From then on it logs a misleading `bounds completely clipped` error even when your artboard is fine.

**What `--local` does:** it replaces `<name>-assets/` on the NAS with a symlink to `~/.psmirror/assets/…`. Generator sees the same path, but files land on local disk, so `rename()` works. This also happens automatically for new versions you create with Save As (v3 → v4) while psmirror is running.

**If Generator is already stuck:** start psmirror with `--local`, then **close and reopen the PSD**. Toggling Image Assets is not enough to reset it.

Local copies never grow without bound: Generator overwrites files instead of adding new ones. To remove folders whose PSD has been moved or deleted:

```sh
psmirror --clean          # list only
psmirror --clean --yes    # delete orphans
```

Don't `rm -rf ~/.psmirror/assets`: the folders that are still in use would leave broken symlinks behind, and Generator would fail again.

## All options

```text
psmirror <a.psd> [b.psd ...]   watch one or more PSDs
psmirror <folder>              watch every *-assets folder below it
psmirror                       reuse the last sources
  --local                      PSD on a network drive: keep output on local disk
  --depth N                    how deep to search a folder for *-assets (default 3)
  --port N                     port (default 8000, +1 if taken)
  --new-token                  new private URL; old links stop working
  --no-token                   no token: anyone on the network can view
psmirror --clean [--yes]       list / remove orphaned local folders
```

## Troubleshooting

**"Connected, but there are no images"**
- Is **File > Generate > Image Assets** still ticked in that PSD?
- Does the artboard name end in `.png`?
- Pointed at a folder? It only searches 3 levels deep. Point closer to the PSDs, or use `--depth 5`.

**The phone can't load the page**
- Same Wi-Fi on both devices? Guest networks often block device-to-device traffic.
- macOS Firewall: allow incoming connections for Python.
- Your Mac's IP can change after a restart. Use the URL printed this time.

**Text looks blurry on the phone**
A 750px design is stretched on a 1179px-wide iPhone. Name the artboard `200% preview.png`.

**Still stuck?** Read Generator's log:

```sh
tail -f ~/Library/Logs/Adobe/Adobe\ Photoshop\ */Generator/generator_latest.txt
```

`Render complete` means Generator is working. `EXDEV` means you need `--local`. If the log just stops, another Generator plugin may have crashed the process.

## How it works

```text
Photoshop ─Image Assets─▶ <name>-assets/preview.png
                                │
                psmirror (Python HTTP server on your Mac)
                                │  Wi-Fi
                         phone browser
              HEAD every 0.6 s → reload when Last-Modified / size change
```

The new image is preloaded before it replaces the old one, so the screen never flashes. Directory scanning runs in a background thread and slows itself down on slow network drives.

## License

MIT

Photoshop is a trademark of Adobe Inc. This project is not affiliated with or endorsed by Adobe.

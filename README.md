# Englex Listening

Standalone Russian-language B1–B2 listening trainer, built from the user's downloaded lesson archive. Public GitHub Pages link: https://evgk724.github.io/Englex_Listening/

Library: 168 recordings, 6.31 hours, about 314 MiB. There are 89 original audio files and 79 audio tracks extracted from videos. 145 recordings have source text; two of these source texts end early and are marked as partial. The remaining 23 recordings are explicitly marked as having no transcript.

The original downloadable audio is preserved. Video is converted into audio-only MP3 at 64 kbps mono; no videos, download scripts, source account pages, credentials or export link lists are published. Transcripts are paired by course, lesson, page and player order. Missing transcripts are clearly marked, and are never replaced by answer keys or a transcript from another player. Lesson transcripts and user progress are separate.

Practice: first listening with hidden text, optional dictation, retelling, playback speed, A/B loops with response pauses, saved audio fragments and optional personal transcripts, spaced return based only on explicit user ratings. No scores, invented learning history, analytics, login or external runtime dependencies. This independent personal tool is not an official Englex product. Rights to source materials remain with their respective owners.

The shell and texts are cached by a service worker. Users may save individual audio tracks, one course or all audio. Cached MP3s support byte ranges for Safari. Offline readiness is based on files actually stored; partial downloads can be resumed. Progress and notes are stored locally and can be exported/imported as JSON. Clearing website data may remove both progress and downloads. Different browsers, devices and Home Screen apps may have separate storage.

## Build

Python 3 with mutagen, and imageio-ffmpeg to extract video sound:

```
python3 scripts/import_archive.py /path/to/export.zip --videos
python3 scripts/build_catalog.py
```

Original per-lesson texts, archive paths, importer audits and scratch media stay in ignored `private/`. Never commit it. Build output is in `docs/`. Publish `docs/` from branch `codex/englex-listening`. Verify source/audio pairing, actual Chromium/WebKit playback, fragment loops, persistence, responsive layouts and offline byte ranges before release. Bump the shell cache when app assets or catalog change.

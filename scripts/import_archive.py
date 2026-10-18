"""Read the user's export as data. Never execute archived scripts or extract video."""
import argparse
import hashlib
import json
import re
import sys
import subprocess
import tempfile
import shutil
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'englex-tools'))
from mutagen.mp3 import MP3

HEADER = re.compile(r'^=== (.*?) — страница (\d+) из (\d+) ===\s*$', re.M)

def fixed(name):
    try:
        return name.encode('cp437').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name

def clean(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'(?<=\w)ˈ|ˈ(?=\w)', "'", text)
    return text.strip()

def main():
    arg = argparse.ArgumentParser()
    arg.add_argument('archive', type=Path)
    arg.add_argument('--videos', action='store_true')
    args = arg.parse_args()
    out = ROOT / 'private'
    (out / 'audio').mkdir(parents=True, exist_ok=True)
    lessons, audio = {}, []
    with ZipFile(args.archive) as z:
        entries = [(fixed(i.filename), i) for i in z.infolist() if not i.is_dir()]
        # Only per-lesson text, not duplicated combined exports, link lists or scripts.
        for name, info in entries:
            path = PurePosixPath(name)
            if len(path.parts) != 4 or path.suffix.lower() != '.txt':
                continue
            raw = clean(z.read(info).decode('utf-8-sig'))
            marks = list(HEADER.finditer(raw))
            pages = []
            for ix, mark in enumerate(marks):
                body = raw[mark.end():marks[ix+1].start() if ix+1 < len(marks) else len(raw)]
                body = re.split(r'Файлы этой страницы:', body)[0].strip()
                pages.append({'number': int(mark[2]), 'text': body})
            if not pages:
                continue
            course = path.parts[1]
            course_id = 'b2' if 'B2' in course else ('b1-2' if 'Part 2' in course else 'b1-1')
            number = int(re.match(r'\d+', path.parts[2])[0])
            lid = f'{course_id}-{number:02d}'
            lessons[str(path.parent)] = {'id': lid, 'course': course_id, 'level': 'B2' if course_id == 'b2' else 'B1', 'number': number, 'title': marks[0][1], 'pages': pages}
        for name, info in entries:
            path = PurePosixPath(name)
            parent = str(path.parent)
            if parent not in lessons or path.suffix.lower() in ('.txt', '.sh'):
                continue
            video = path.suffix.lower() == '.mp4'
            if video and not args.videos:
                continue
            with z.open(info) as stream:
                head = stream.read(12)
            if not (video or path.suffix.lower() == '.mp3' or head.startswith(b'ID3') or head[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2')):
                continue
            match = re.search(r'стр (\d+) видео (\d+)' if video else r'стр (\d+)-(\d+)', path.name)
            if not match:
                raise ValueError(f'Unrecognised audio name: {name}')
            lesson = lessons[parent]
            page, ordinal = map(int, match.groups())
            aid = f'{lesson["id"]}-{"v" if video else "p"}{page:02d}-{ordinal}'
            dest = out / 'audio' / f'{aid}.mp3'
            if video:
                import imageio_ffmpeg
                if not dest.exists():
                    with tempfile.TemporaryDirectory(dir=out) as temporary:
                        source = Path(temporary) / 'source.mp4'
                        with z.open(info) as src, source.open('wb') as target:
                            shutil.copyfileobj(src, target)
                        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error', '-i', str(source), '-map', '0:a:0', '-vn', '-map_metadata', '-1', '-ac', '1', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '64k', '-threads', '1', str(dest)], check=True)
                data = dest.read_bytes()
            else:
                data = z.read(info)  # CRC checked by ZipFile.
                dest.write_bytes(data)
            media = MP3(dest)
            page_text = next((p['text'] for p in lesson['pages'] if p['number'] == page), '')
            audio.append({'id': aid, 'lessonId': lesson['id'], 'course': lesson['course'], 'level': lesson['level'], 'title': lesson['title'], 'lessonNumber': lesson['number'], 'page': page, 'ordinal': ordinal, 'kind': 'video-audio' if video else 'audio', 'duration': round(media.info.length, 3), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'pageText': page_text, 'archiveName': path.name})
            if len(audio) % 15 == 0:
                print(f'Imported {len(audio)} tracks', flush=True)
    audio.sort(key=lambda a: (a['course'], a['lessonNumber'], a['page'], a['ordinal']))
    catalog = {'source': args.archive.name, 'lessons': sorted(lessons.values(), key=lambda a: (a['course'], a['number'])), 'tracks': audio}
    (out / 'source.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
    audit = []
    seen = set()
    for a in audio:
        key = (a['lessonId'], a['page'])
        if key in seen:
            continue
        seen.add(key)
        group = [t for t in audio if (t['lessonId'],t['page']) == key]
        audit.append('\n'.join(['='*80, f'{a["lessonId"]} | {a["title"]} | PAGE {a["page"]}', 'AUDIO: '+', '.join(f'{t["id"]} = {t["duration"]:.1f}s' for t in group), a['pageText']]))
    (out / 'audio-pages.txt').write_text('\n\n'.join(audit))
    print(json.dumps({'tracks':len(audio), 'lessons':len(lessons), 'audioLessons':len({a['lessonId'] for a in audio}), 'audioMiB': round(sum(a['bytes'] for a in audio)/1024**2,2), 'audioHours':round(sum(a['duration'] for a in audio)/3600,2), 'courses':dict(Counter(a['course'] for a in audio)), 'missingPages':[a['id'] for a in audio if not a['pageText']]},ensure_ascii=False))

if __name__ == '__main__':
    main()

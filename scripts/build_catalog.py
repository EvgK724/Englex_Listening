"""Publish audio and the associated spoken text only; keep the original export private."""
import json
import re
import shutil
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
STOP=re.compile(r'^(?:Glossary$|[\ue000-\uf8ff]|(?:Choose (?:the|True|an|which|a |what)|Match |Complete (?:the|each|part)|Сomplete |Answer (?:the|these)|Put |Listen (?:to |again|and )|Read (?:the |again)|Discuss (?:the|these)|Fill |Tick |Write |Compare |Make (?:sentences|a list)|Act out |For each person )|[— ]{3,}$|\d+\.\d+\s)')
EXTRA_END={
 'b1-1-11-p02-1':'Which ways of cheering up',
 'b1-1-13-v07-1':'Watch the video to the end.',
 'b1-1-47-v02-1':'Did the guy like the quiz?',
 'b2-07-v10-1':'What do you think the reporter’s aim was',
 'b1-1-16-p06-1':'Which of the speakers',
 'b1-1-26-p02-1':"Is your recipe different",
 'b1-1-40-p11-1':'In which situation did Tom',
 'b1-1-42-p14-1':'emotional, caring, tough',
 'b1-1-44-p03-1':'Who asks',
 'b1-1-45-p02-1':'Picture 3',
 'b1-1-64-p02-1':'What can’t the three friends agree on?',
 'b1-1-68-p04-1':'Who are the people talking about?',
 'b1-2-20-p13-1':'Who do you think had the best night?',
 'b1-2-26-p05-1':'Whose journey was worse',
 'b2-08-p15-1':'1. Patrick is talking',
 'b2-09-p08-1':"What should you do if you want to improve everyone's health?",
}
NO_TEXT={'b1-1-06-v16-1','b1-1-15-p13-1','b1-1-15-p13-2','b1-1-15-p13-3','b1-1-16-p06-2','b1-1-37-p01-1','b2-04-p05-1','b2-07-p09-1'}
PARTIAL={'b1-1-23-v10-1','b1-2-28-v25-1'}
OVERRIDES={'b2-04-p02-2':"Riley:\nWow, what a great shot!\nEmma:\nIt’s all right.\nRiley:\nYou know just how to get a really good shot. The light is amazing.\nEmma:\nThanks. Guess it’s not bad."}

def extract(t):
    if t['id'] in NO_TEXT:return '', 'missing'
    if t['id'] in OVERRIDES:return OVERRIDES[t['id']], 'archive'
    lines=[x.strip() for x in t['pageText'].splitlines() if x.strip()]
    markers=[i for i,x in enumerate(lines) if re.fullmatch(r'\d{1,2}:\d{2}',x)]
    if len(markers)<t['ordinal']:return '', 'missing'
    start=markers[t['ordinal']-1]+1
    end=len(lines)
    for j in range(start,len(lines)):
        prev=lines[j-1] if j else ''
        if re.fullmatch(r'\d{1,2}:\d{2}',lines[j]) or (STOP.match(lines[j]) and not prev.endswith(':')):
            end=j;break
    raw='\n'.join(lines[start:end]).strip()
    raw=raw.split('*Компания Meta Platforms')[0].strip()
    raw=raw.replace('Facebook*','Facebook').replace('Instagram*','Instagram')
    if t['id'] in EXTRA_END:
        raw=raw.split(EXTRA_END[t['id']])[0].strip()
        raw=re.sub(r'\n\d+\.$','',raw)
    # Empty transcript panels expose exercise questions, not spoken words.
    if len(raw.split())<(6 if t['duration']<15 else 12) or re.match(r'^(?:Which (?:things|of)|Do you often|What do you think about (?:the|this) video|What does the video)',raw):return '', 'missing'
    return raw,'archive'

def paragraphs(text):
    result=[];speaker=''
    for line in text.splitlines():
        line=line.strip()
        if not line:continue
        if len(line)<65 and line.endswith(':'):
            speaker=line[:-1];continue
        # Strip private-use UI glyphs and export artefacts.
        line=re.sub('[\ue000-\uf8ff]','',line)
        line=line.replace('licenсe','licence')
        result.append({'speaker':speaker,'text':line});speaker=''
    return result

def main():
    source=json.loads((ROOT/'private/source.json').read_text())
    docs=ROOT/'docs';(docs/'audio').mkdir(parents=True,exist_ok=True)
    tracks=[];audit=[]
    for t in source['tracks']:
        raw,origin=extract(t)
        published={k:t[k] for k in ['id','lessonId','course','level','title','lessonNumber','page','ordinal','kind','duration','bytes','sha256']}
        published.update(audio=f'audio/{t["id"]}.mp3',transcript=paragraphs(raw),transcriptOrigin=origin)
        if t['id'] in PARTIAL:published['transcriptPartial']=True
        tracks.append(published)
        target=docs/'audio'/f'{t["id"]}.mp3'
        if not target.exists() or target.stat().st_size!=t['bytes']:
            shutil.copyfile(ROOT/'private/audio'/f'{t["id"]}.mp3',target)
        audit.append({'id':t['id'],'kind':t['kind'],'duration':t['duration'],'words':len(raw.split()),'start':raw[:150],'end':raw[-220:],'origin':origin})
    catalog={'version':'2026.10.19.1','tracks':tracks}
    (docs/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    (ROOT/'private/transcript-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print(json.dumps({'tracks':len(tracks),'withTranscript':sum(bool(t['transcript']) for t in tracks),'kinds':dict(Counter(t['kind'] for t in tracks)),'missing':[a['id'] for a in audit if not a['words']],'audioMiB':round(sum(t['bytes'] for t in tracks)/1048576,1)},ensure_ascii=False))

if __name__=='__main__':main()

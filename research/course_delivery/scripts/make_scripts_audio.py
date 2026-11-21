"""Create bilingual speaker guides and explicitly synthetic offline rehearsal audio."""
import json,ctypes,wave,re,textwrap
from pathlib import Path
D=Path(__file__).resolve().parents[1];ROOT=D.parents[1]
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--records',type=Path,required=True);args=parser.parse_args();OP=args.records.resolve();OP.mkdir(parents=True,exist_ok=True);AUDIO=OP/'audio';AUDIO.mkdir(exist_ok=True)
slides=json.loads((D/'source/slide_content.json').read_text())['slides'];lib=ctypes.CDLL('libespeak-ng.so.1');lib.espeak_Initialize.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int];rate=lib.espeak_Initialize(2,0,None,0);assert rate>0
chunks=[];CB=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.POINTER(ctypes.c_short),ctypes.c_int,ctypes.c_void_p)
@CB
def callback(p,n,e):
 if p and n:chunks.append(ctypes.string_at(p,n*2))
 return 0
lib.espeak_SetSynthCallback(callback);assert lib.espeak_SetVoiceByName(b'en-us')==0

def synth(speed):
 lib.espeak_SetParameter(1,speed,0);result=[];current=0
 for s in slides:
  chunks.clear();t=s['en'].encode('utf-8')
  if t:lib.espeak_Synth(t,len(t)+1,0,1,0,1,None,None);lib.espeak_Synchronize()
  raw=b''.join(chunks);duration=len(raw)/2/rate;end=duration+2+(12 if s['kind']=='video' else 0)
  if not t:end=5
  with wave.open(str(AUDIO/f"slide_{s['number']:02d}.wav"),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(raw if raw else b'\0\0'*int(rate*.1))
  result.append(dict(slide=s['number'],title=s['title'],start_s=current,voice_s=duration,duration_s=end,kind=s['kind'],family=s.get('family'),excerpt_start=s.get('excerpt_start')));current+=end
 return result,current
plan,total=synth(160)
if total>590:plan,total=synth(175)
assert total<=590,total
(D/'source/rehearsal_timing.json').write_text(json.dumps(dict(duration_s=total,voice='Offline eSpeak NG en-us; synthetic rehearsal, not a recording of team members',sample_rate=rate,segments=plan),indent=2)+'\n')
def stamp(t):return f'{int(t//60):02d}:{int(t%60):02d}'
def srt_stamp(t):
 m=int(round(t*1000));return f'{m//3600000:02d}:{m//60000%60:02d}:{m//1000%60:02d},{m%1000:03d}'
en=['# English presentation script','',f'Total rehearsal duration: **{stamp(total)}**. The spoken script contains {sum(len(s["en"].split()) for s in slides)} words. Aim for roughly 150–160 words per minute; actual human recording time will vary.','', '**Review copy:** replace the pending group identity, names and actual work shares before recording. The supplied MP4 uses synthetic rehearsal narration; it is not a recording of the group.','']
zh=['# 中文逐页讲解提示','',f'英文讲稿与 PPT 备注逐页对应，合成旁白练习版总时长约 {stamp(total)}。以下用于理解逻辑，不是必须逐字翻译。','']
srt=[];counter=0
for s,t in zip(slides,plan):
 en += [f'## Slide {s["number"]:02d} — {s["title"]}',f'**{stamp(t["start_s"])}–{stamp(t["start_s"]+t["duration_s"])}**', '',s['en'] or 'Reference page; no additional spoken content.','']
 if s['kind']=='video':en += ['**Video cue:** after the spoken explanation, show the 12-second excerpt. In PowerPoint, click the embedded full video if discussing it live.','']
 zh += [f'## 第 {s["number"]} 页｜{s["title"]}',f'时间：{stamp(t["start_s"])}–{stamp(t["start_s"]+t["duration_s"])}', '',s['zh'],'']
 if s['en']:
  words=s['en'].split();segments=[' '.join(words[i:i+17]) for i in range(0,len(words),17)]
  for i,text in enumerate(segments):
   counter+=1;start=t['start_s']+i*t['voice_s']/len(segments);end=t['start_s']+(i+1)*t['voice_s']/len(segments)
   srt += [str(counter),srt_stamp(start)+' --> '+srt_stamp(end),'\n'.join(textwrap.wrap(text,48)),'']
(D/'presentation/English_Speaker_Script.md').write_text('\n'.join(en).rstrip()+'\n');(D/'presentation/中文逐页讲解提示.md').write_text('\n'.join(zh).rstrip()+'\n');(D/'presentation/INFH5000_Rehearsal.en.srt').write_text('\n'.join(srt).rstrip()+'\n')
def tex(s):
 for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('–','--'),('—','---'),('×',r'$\times$')]:s=s.replace(a,b)
 return s
body=r'''\documentclass[a4paper,11pt]{article}
\usepackage[margin=22mm]{geometry}\usepackage[T1]{fontenc}\usepackage{lmodern,microtype,hyperref,setspace}\hypersetup{hidelinks}\setstretch{1.18}\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}
\title{INFH5000 Urban Robot Navigation\\English Speaker Script}\author{Group information pending}\date{21 November 2026}
\begin{document}\maketitle
This script follows the 17-slide deck. The synthetic rehearsal runs for '''+stamp(total)+r'''. Team identity and actual contribution shares must be confirmed before recording. Video excerpts add 12 seconds after each demonstration explanation. Script-timed subtitles are approximate, not forced-aligned transcription.
'''
for s,t in zip(slides,plan):body+=r'\section*{Slide '+str(s['number'])+': '+tex(s['title'])+'}\n'+r'\textit{'+stamp(t['start_s'])+'--'+stamp(t['start_s']+t['duration_s'])+'}\n\n'+tex(s['en'] or 'Reference page; no spoken content.')+'\n\n'
body+=r'\end{document}';(D/'presentation/English_Speaker_Script.tex').write_text(body)
print('SPEAKER_GUIDES_AND_LOCAL_AUDIO_READY',round(total,2),'seconds',stamp(total))

"""Render an explicitly synthetic, timed MP4 with genuine native video excerpts."""
import json,subprocess,re,concurrent.futures
from pathlib import Path
import imageio_ffmpeg
D=Path(__file__).resolve().parents[1];ROOT=D.parents[1];import argparse
parser=argparse.ArgumentParser();parser.add_argument('--records',type=Path,required=True);parser.add_argument('--only',type=int,nargs='*');args=parser.parse_args();OP=args.records.resolve();FF=imageio_ffmpeg.get_ffmpeg_exe();timing=json.loads((D/'source/rehearsal_timing.json').read_text());segments=timing['segments'];OUT=OP/'video_segments';OUT.mkdir(exist_ok=True);font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def encode(t):
 n=t['slide'];png=OP/f'final_slide-{n:02d}.png';assert png.is_file();wav=OP/f'audio/slide_{n:02d}.wav';target=OUT/f'{n:02d}.mp4';duration=t['duration_s']
 args=[FF,'-hide_banner','-loglevel','error','-y','-loop','1','-framerate','15','-i',str(png),'-i',str(wav)]
 watermark=f"drawbox=x=0:y=0:w=iw:h=18:color=0x173b59:t=fill,drawtext=fontfile={font}:text='SYNTHETIC REHEARSAL  |  TEAM INFORMATION PENDING':fontcolor=white:fontsize=11:x=(w-tw)/2:y=2"
 if t['kind']=='video':
  video=ROOT/f"research/results/videos/native_{t['family']}_comparison.mp4";args+=['-ss',str(t['excerpt_start']),'-t','12','-i',str(video)]
  start=t['voice_s']+1
  # The movie occupies the same region as its editable PPT media object.
  filters=f"[2:v]scale=1166:335,setsar=1,setpts=PTS-STARTPTS+{start}/TB[clip];[0:v][clip]overlay=58:195:eof_action=pass:enable='between(t,{start},{start+12})'[base];[base]{watermark},format=yuv420p[v]"
 else:filters=f'[0:v]{watermark},format=yuv420p[v]'
 args+=['-filter_complex',filters,'-map','[v]','-map','1:a:0','-af','apad','-t',f'{duration:.6f}','-r','15','-c:v','libx264','-preset','veryfast','-crf','23','-threads','2','-c:a','aac','-b:a','80k','-ar','48000','-ac','1','-movflags','+faststart',str(target)]
 log=OP/f'encode_{n:02d}.log'
 with log.open('w') as f:subprocess.run(args,stdout=f,stderr=f,check=True)
 print('SEGMENT_READY',n,round(duration,2),flush=True);return target

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(encode,[t for t in segments if not args.only or t['slide'] in args.only]))
files=[OUT/f"{t['slide']:02d}.mp4" for t in segments];assert all(p.is_file() for p in files)
concat=OP/'video_concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in files));output=D/'presentation/INFH5000_Narrated_Rehearsal.mp4'
subprocess.run([FF,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(output)],check=True)
probe=subprocess.run([FF,'-i',str(output)],capture_output=True,text=True).stderr
match=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',probe);assert match,probe
actual=3600*int(match[1])+60*int(match[2])+float(match[3]);assert actual<=600,actual
result=dict(duration_s=actual,under_10_minutes=True,format='MP4',video_codec='H264',audio_codec='AAC',resolution=[1280,720],fps=15,synthetic_narration=True,group_information_pending=True,native_video_excerpt_count=3,source_timeline='source/rehearsal_timing.json',bytes=output.stat().st_size)
(D/'presentation/rehearsal_metadata.json').write_text(json.dumps(result,indent=2)+'\n');(OP/'rehearsal_probe.txt').write_text(probe);print('REHEARSAL_MP4_COMPLETE',json.dumps(result),flush=True)

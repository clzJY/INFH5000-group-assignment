"""Compare native recordings at 2x playback, retaining failed demonstrations."""
import json,math
from pathlib import Path
import imageio.v2 as imageio
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
NAMES={'rpp':'RPP-inspired','lattice':'Rule local planner','lora':'Adapted vision-language model'}

def main():
    base=ROOT/'research/runs/native_demonstrations';out=ROOT/'research/results/videos';out.mkdir(parents=True,exist_ok=True)
    fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(fontfile,15);small=ImageFont.truetype(fontfile,13)
    results=[]
    for family in ('X','S','SC'):
        folders=[base/f'{family}_wide_p5_s1502_{m}' for m in ('rpp','lattice','lora')]
        summaries=[json.loads((r/'summary.json').read_text()) for r in folders]
        assert all(s['status']=='complete' for s in summaries)
        assert len({s['initial_fingerprint'] for s in summaries})==1
        readers=[imageio.get_reader(r/'rollout.mp4') for r in folders]
        lengths=[r.count_frames() for r in readers];traces=[[json.loads(x) for x in (r/'steps.jsonl').read_text().splitlines()] for r in folders]
        target=out/('native_'+family+'_comparison.mp4')
        with imageio.get_writer(target,fps=10,codec='libx264',macro_block_size=1,ffmpeg_params=['-crf','20','-pix_fmt','yuv420p']) as writer:
            last=[None]*3
            for frame in range(max(lengths)):
                canvas=Image.new('RGB',(1440,414),'#f8f8f8');draw=ImageDraw.Draw(canvas)
                for j,(reader,length,s,trace) in enumerate(zip(readers,lengths,summaries,traces)):
                    index=min(frame,length-1)
                    if frame<length:last[j]=reader.get_data(index)
                    canvas.paste(Image.fromarray(last[j]),(j*480,65))
                    t=min((2*index+1)*.1,s['duration_s']);row=trace[min(2*index,len(trace)-1)]
                    draw.text((j*480+10,5),NAMES[s['method']],fill='black',font=font)
                    draw.text((j*480+10,25),f"Final: arrival={'YES' if s['strict_goal'] else 'NO'}, contact={'YES' if s['any_contact'] else 'NO'}",fill='black',font=small)
                    status='held after run ended' if frame>=length else 'native recorded motion'
                    draw.text((j*480+10,44),f"t={t:.1f}s | {status}",fill='black',font=small)
                    draw.text((j*480+10,387),f"Sampled footprint: {'OUTSIDE' if row['outside_walkable'] else 'inside'} walkable union",fill='black',font=small)
                draw.text((10,402),f"{family}: fixed demonstration seed 1502 | 2x simulated playback | Ended runs hold their last recorded view",fill='black',font=ImageFont.truetype(fontfile,10))
                writer.append_data(np.asarray(canvas))
        for r in readers:r.close()
        results.append(dict(family=family,path=str(target.relative_to(ROOT)),frames=max(lengths),output_fps=10,native_fps=5,episodes=[{k:s[k] for k in ('method','seed','strict_goal','contact_free','any_contact','duration_s','outside_walkable_fraction')} for s in summaries]))
    (out/'manifest.json').write_text(json.dumps(results,indent=2)+'\n')
    print('NATIVE_COMPARISON_VIDEOS_COMPLETE',len(results))

if __name__=='__main__':main()

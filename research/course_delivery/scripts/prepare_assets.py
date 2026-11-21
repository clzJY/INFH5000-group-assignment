"""Prepare course graphics strictly from recorded native views and audited data."""
from pathlib import Path
import json,shutil,subprocess
import imageio_ffmpeg
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'research/course_delivery';A=D/'assets';A.mkdir(exist_ok=True)
for name in ['scene_atlas.png','pipeline.png','main_results.png']:shutil.copyfile(ROOT/'research/results/figures'/name,A/name)
for m in ['X','S','SC']:
 src=ROOT/'research/runs/main_classical_v1'/f'{m}_wide_p5_s1600_lattice/first_frame.png';shutil.copyfile(src,A/f'scene_{m}.png')
 # Media stays in its original repository path; embedded in PPT, copied into delivery ZIP only.
 ff=imageio_ffmpeg.get_ffmpeg_exe();video=ROOT/f'research/results/videos/native_{m}_comparison.mp4'
 subprocess.run([ff,'-v','error','-y','-ss','12','-i',str(video),'-frames:v','1',str(A/f'poster_{m}.png')],check=True)
data=json.loads((ROOT/'research/training_data/dataset.json').read_text());r=next(r for r in data['train'] if r['label'] in (0,1,3,4));src=ROOT/r['image'];shutil.copyfile(src,A/'actual_training_input.png')
(A/'training_input_identity.json').write_text(json.dumps(dict(image_sha256=r['image_sha256'],label=r['label'],condition=r['condition'],step=r['step'],description='Actual training composite; native RGB and privileged local map. No teacher score is drawn.'),indent=2)+'\n')
source={}
for name in ['core','variation','ablations','holdout','challenge']:
 source[name]=json.loads((ROOT/f'research/results/{name}/summary.json').read_text())
source['paired']=json.loads((ROOT/'research/results/core/paired.json').read_text());source['contrasts']=json.loads((ROOT/'research/results/core/additional_contrasts.json').read_text());source['strata']=json.loads((ROOT/'research/results/core/spatial_strata.json').read_text());source['videos']=json.loads((ROOT/'research/results/videos/manifest.json').read_text());source['provenance']=json.loads((ROOT/'research/results/provenance_audit.json').read_text());(D/'source/audited_content.json').write_text(json.dumps(source,indent=2)+'\n')
print('NATIVE_ASSETS_PREPARED')

# A course-sized schematic keeps labels readable in the 12-point report.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
fig,ax=plt.subplots(figsize=(7.4,2.8));ax.set_xlim(0,7.4);ax.set_ylim(0,2.8);ax.axis('off')
boxes=[(.08,1.72,'RGB + map\n+ instruction'),(2.65,1.72,'Vision / text\nLoRA'),(5.22,1.72,'A–F proposal\n1 Hz'),(.08,.55,'Route + five paths\n+ stopping'),(2.65,.55,'Geometry checks\n10 Hz'),(5.22,.55,'Native wheel\nphysics')]
for x,y,label in boxes:
 ax.add_patch(FancyBboxPatch((x,y),2.05,.67,boxstyle='round,pad=.025',facecolor='#edf3f5',edgecolor='#577085',linewidth=.8));ax.text(x+1.025,y+.335,label,ha='center',va='center',fontsize=12.5)
for y in (2.055,.885):
 for x in (2.16,4.73):ax.annotate('',(x+.41,y),(x,y),arrowprops={'arrowstyle':'->','color':'#173b59','lw':1.2})
ax.plot([6.24,6.24,3.68],[1.69,1.38,1.38],color='#173b59',lw=1.1);ax.annotate('',(3.68,1.25),(3.68,1.38),arrowprops={'arrowstyle':'->','color':'#173b59','lw':1.1})
ax.text(3.7,.10,'Invalid proposal → geometric fallback; no feasible path → braking',ha='center',fontsize=11)
fig.tight_layout(pad=.2);fig.savefig(A/'pipeline.png',dpi=240);plt.close(fig)

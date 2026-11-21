/* Editable academic presentation; only recorded native simulation images/video. */
const fs=require('fs'),path=require('path');
let PptxGenJS;try{PptxGenJS=require('pptxgenjs')}catch(e){try{PptxGenJS=require(path.resolve(__dirname,'../source/node_modules/pptxgenjs'))}catch(local){PptxGenJS=require('/data/private/user7/projects/Tempfile/IOTA-share/deepinfer_v1/src/node_modules/pptxgenjs')}}
const D=path.resolve(__dirname,'..'),ROOT=path.resolve(D,'../..'),A=path.join(D,'assets'),OUT=path.join(D,'presentation');
const content=JSON.parse(fs.readFileSync(path.join(D,'source/slide_content.json'))),data=JSON.parse(fs.readFileSync(path.join(D,'source/audited_content.json'))),group=JSON.parse(fs.readFileSync(path.join(D,'source/group_metadata.json')));
const pptx=new PptxGenJS();pptx.layout='LAYOUT_WIDE';pptx.author='INFH5000 group information pending';pptx.title=group.project_title;pptx.subject='Course project; independently audited native simulations';pptx.lang='en-US';pptx.theme={headFontFace:'Noto Sans',bodyFontFace:'Noto Sans',lang:'en-US'};
const W=13.333333,H=7.5,C={black:'111111',navy:'173B59',teal:'24746B',red:'A8463A',gray:'65717C',line:'D7DEE4',light:'F0F4F6',pale:'EAF3F0',white:'FFFFFF',amber:'986123'};
let cur,slide,serial=0;const manifest={status:'complete_review_copy',user_authorized_full_delivery:true,user_confirmed:false,group_identity_pending:true,engine:'PptxGenJS 4.0.1',canvas:{width:W,height:H},slides:[]};
function tx(text,x,y,w,h,size=20,color=C.black,bold=false,extra={}){if(!text)return;slide.addText(text,{x,y,w,h,fontFace:'Noto Sans',fontSize:size,color,bold,margin:0,breakLine:false,vertAnchor:'mid',paraSpaceAfterPt:0,...extra});cur.text_objects.push({id:'t'+(++serial),text,x,y,w,h,font_size_pt:size,editable:true});}
function shape(x,y,w,h,fill=C.light,line=null,extra={}){slide.addShape(pptx.ShapeType.rect,{x,y,w,h,fill:{color:fill},line:{color:line||fill,width:line?.7:0},...extra});cur.native_components.push({type:'shape',x,y,w,h});}
function line(x1,y1,x2,y2,color=C.line,width=1,arrow=false){slide.addShape(pptx.ShapeType.line,{x:Math.min(x1,x2),y:Math.min(y1,y2),w:Math.max(.001,Math.abs(x2-x1)),h:Math.max(.001,Math.abs(y2-y1)),flipH:x2<x1,flipV:y2<y1,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});cur.native_components.push({type:'line',x:Math.min(x1,x2),y:Math.min(y1,y2),w:Math.abs(x2-x1),h:Math.abs(y2-y1)});}
function image(name,x,y,w,h,why='Recorded native simulator view; complex visual evidence, not editable geometry.'){const p=path.join(A,name),b=fs.readFileSync(p);let iw=b.readUInt32BE(16),ih=b.readUInt32BE(20),k=Math.min(w/iw,h/ih),dw=iw*k,dh=ih*k;slide.addImage({path:p,x:x+(w-dw)/2,y:y+(h-dh)/2,w:dw,h:dh});cur.image_assets.push({name,x:x+(w-dw)/2,y:y+(h-dh)/2,w:dw,h:dh,reason:why,editable:false});}
function note(text){shape(.55,6.22,12.23,.48,C.light);tx(text,.72,6.25,11.9,.39,15,C.navy);}
function begin(s){slide=pptx.addSlide();slide.background={color:C.white};cur={number:s.number,title:s.title,kind:s.kind,evidence:s.evidence,text_objects:[],native_components:[],image_assets:[],media_assets:[],speaker_script:s.en,zh_cue:s.zh};manifest.slides.push(cur);tx('INFH5000  /  URBAN ROBOT NAVIGATION',.55,.24,10,.25,11,C.gray);tx(s.title,.55,.78,12.2,.82,s.kind==='cover'?31:29,C.black,true);line(.55,1.65,12.78,1.65,C.line,1);tx(String(s.number).padStart(2,'0'),12.1,7.04,.65,.2,10,C.gray,false,{align:'right'});tx('Sources: '+s.evidence.join(' · '),.55,7.00,11.4,.30,9.3,C.gray);slide.addNotes('ENGLISH SPEAKER SCRIPT\n'+s.en+'\n\n中文提示\n'+s.zh+'\n\nEvidence: '+s.evidence.join('; '));}
function para(text,x,y,w,h,size=21){tx(text,x,y,w,h,size,C.black,false,{valign:'top',breakLine:false});}
function table(headers,rows,x,y,width,rowH=.55,colW=null,size=17){const ws=colW||headers.map(()=>width/headers.length);let xx=x;headers.forEach((t,i)=>{shape(xx,y,ws[i],rowH,C.navy);tx(t,xx+.12,y+.06,ws[i]-.24,rowH-.12,size,C.white,true);xx+=ws[i]});rows.forEach((r,ri)=>{let yy=y+(ri+1)*rowH,xx=x;r.forEach((t,ci)=>{shape(xx,yy,ws[ci],rowH,ri%2?C.white:C.light);tx(String(t),xx+.12,yy+.06,ws[ci]-.24,rowH-.12,size,C.black,ri===4&&safestr(t).includes('Geometric'));xx+=ws[ci]});line(x,yy+rowH,x+width,yy+rowH,C.line,.6)});}
function safestr(x){return String(x)}
function bars(labels,values,x,y,w,max,colors,rowH=.48,valueSuffix='',font=17){const labelW=2.5,chartW=w-labelW-.9;for(let t=0;t<=max;t+=max/4){const xx=x+labelW+chartW*t/max;line(xx,y-.10,xx,y+labels.length*rowH-.04,C.line,.6);tx(String(Math.round(t)),xx-.25,y-.43,.5,.25,11,C.gray,false,{align:'center'})}labels.forEach((l,i)=>{const yy=y+i*rowH;tx(l,x,yy,w-chartW-.95,rowH-.07,font);shape(x+labelW,yy+.08,Math.max(.008,chartW*values[i]/max),rowH-.21,colors?.[i]||C.teal);tx(String(values[i])+valueSuffix,x+labelW+chartW*values[i]/max+.10,yy+.02,.85,rowH-.07,font,C.black,true)});}
const all=Object.fromEntries(data.core.filter(r=>r.map==='all').map(r=>[r.method,r]));
for(const s of content.slides){begin(s);
if(s.kind==='cover'){
 image('hkust_logo.png',10.1,.19,2.65,.55,'University logo extracted from the course-mandated CC BY 4.0 report template.');
 tx('Three-scene native simulation study',.58,1.95,11.8,.5,23,C.navy);tx('Group ID: '+(group.group_id||'TO BE CONFIRMED')+'   |   21 November 2026',.58,2.58,11.8,.42,19,C.gray);
 table(['Member','Thrust','Work share','Actual work'],group.members.map(m=>[m.name||'To be confirmed',m.thrust||'Pending',m.contribution_percent==null?'Pending':m.contribution_percent+'%',m.actual_work||'To be agreed']),.58,3.28,12.15,group.members.length===5?.43:.49,[3.0,2.1,2.05,5.0],15);
 tx('AI × DATA SCIENCE × COMPUTATIONAL MEDIA',.58,6.13,11.5,.4,18,C.navy,true);tx('Review copy: confirm 4–5 members, thrust rule and work shares totalling 100% before submission.',.58,6.65,11.6,.34,12,C.red);
}else if(s.kind==='problem'){
 tx('RQ1',.6,1.98,1,.45,28,C.teal,true);para('Does local trajectory selection improve contact-free completion?',1.65,1.95,10.7,.9,25);
 tx('RQ2',.6,3.02,1,.45,28,C.navy,true);para('Does vision–language guidance improve on geometric selection?',1.65,3.0,10.7,.9,25);
 ['AI','Data science','Computational media'].forEach((t,i)=>{const x=.6+i*4.15;line(x,4.25,x+3.8,4.25,C.teal,3);tx(t,x,4.48,3.8,.4,21,C.black,true);para(['Multimodal action adaptation\nTeacher imitation','Matched conditions\nBootstrap and ablations','Procedural 3D scenes\nNative visual demonstrations'][i],x,5.0,3.8,.9,19)});
 note('A shared-space navigation study; no physical IoT network or real-city digital twin is claimed.');
}else if(s.kind==='scenes'){
 ['X','S','SC'].forEach((f,i)=>{const x=.55+i*4.15;tx(['Intersection','Straight sidewalk','Curved street'][i],x,1.9,3.85,.4,21,C.navy,true);image('scene_'+f+'.png',x,2.45,3.85,2.35);});
 table(['Scene families','Clear-width bands','Pedestrian counts','Fresh seeds'],[['3','2: 2.6 / 4.6 m','2: 5 / 15 agents','10 per family']],.55,5.0,12.2,.48,[2.7,3.2,3.35,2.95],17);
 note('3 × 2 × 2 × 10 = 120 matched conditions per method; agent counts are not crowd density.');
}else if(s.kind==='novelty'){
 table(['Component','Retained pilot','Completed extension'],[['Scenes','Single-scene study','Three families; width / crowd factors'],['Navigation','Tracking + speed prediction','Lateral trajectories + geometry checks'],['Learning','No VLM adaptation','Actual vision / text LoRA training'],['Evidence','Original pilot kept separate','1,384 formal episodes + diagnostics']],.55,2.0,12.2,.77,[2.0,4.15,6.05],18);
 note('Novelty is the implemented extension and comparative evidence; established methods remain attributed.');
}else if(s.kind==='pipeline'){
 const box=(x,y,w,title,sub,fill=C.light)=>{shape(x,y,w,1.18,fill);tx(title,x+.15,y+.10,w-.3,.60,18,C.black,true);tx(sub,x+.15,y+.81,w-.3,.26,14,C.gray)};
 box(.65,2.02,3.35,'RGB + map + instruction','Current frame; privileged map');box(4.83,2.02,3.35,'Vision / text LoRA','Six restricted action labels');box(9.0,2.02,3.35,'A–F proposal','High-level choice: 1 Hz');
 line(4.02,2.55,4.7,2.55,C.navy,2,true);line(8.2,2.55,8.88,2.55,C.navy,2,true);
 box(.65,4.05,3.35,'Route + candidate library','Five lateral paths + stop');box(4.83,4.05,3.35,'Geometric revalidation','Footprints + motion + region',C.pale);box(9.0,4.05,3.35,'Native wheel physics','Steering, throttle and brake');
 line(4.02,4.58,4.7,4.58,C.teal,2,true);line(8.2,4.58,8.88,4.58,C.teal,2,true);line(10.67,3.24,10.67,3.62,C.navy,1.5);line(10.67,3.62,6.5,3.62,C.navy,1.5);line(6.5,3.62,6.5,3.97,C.navy,1.5,true);
 tx('Invalid proposal → geometric fallback; no feasible candidate → physical braking',.8,5.48,11.9,.4,19,C.navy);
 note('Checks and native actuation: 10 Hz. The controller never overwrites robot pose or velocity.');
}else if(s.kind==='training'){
 image('actual_training_input.png',.6,2.0,7.1,3.55);tx('Actual training composite: native RGB + privileged map',.6,5.58,7.1,.43,15,C.gray);
 table(['Training item','Setting'],[['Train / validation','598 / 304 decisions'],['Trainable / frozen','1.11M / backbone'],['LoRA rank / alpha','8 / 16'],['Batch / epochs','4 / 10'],['Seeds','0, 1, 2 + holdout']],8.0,1.96,4.74,.65,[2.37,2.37],17);
 note('Geometric predictive labels → supervised imitation; validation selects checkpoints, never test outcomes.');
}else if(s.kind==='baselines'){
 table(['Method','Decision mechanism','Comparison purpose'],[['RPP-inspired','Regulated reference tracking','Classical route follower'],['Speed forecast','Predict route occupancy; change speed','Timing without lateral choices'],['DWA-style','Local command search','Earlier search adaptation'],['MPPI-style','Sample 96 control sequences','Flexible sampled local control'],['Geometric selector','Rank lateral candidates + stop','New hierarchy without a model'],['Frozen VLM','Pretrained A–F token choice','Direct pretrained action use'],['Adapted VLM','Vision / text LoRA token choice','Task adaptation and added value']],.55,1.96,12.2,.51,[2.35,4.55,5.3],16);
 note('Project implementations. Old controllers lack the new candidate filter; model observations omit explicit velocity.');
}else if(s.kind==='protocol'){
 table(['Formal suite','n','Purpose'],[['Natural comparison','840','7 × 120 conditions'],['Training-seed variation','240','2 seeds × 120'],['Input removals','96','4 variants × 24'],['Curve holdout','40','Excluded family test'],['Post-planning blockage','168','7 methods × 24']],.55,1.96,7.0,.60,[3.25,1.1,2.65],16);
 tx('STRICT ARRIVAL',8.05,2.02,4.5,.35,20,C.navy,true);para('Native flag AND\nendpoint distance ≤ 2 m',8.05,2.5,4.5,.9,22);
 tx('CONTACT-FREE ARRIVAL',8.05,3.77,4.6,.35,20,C.teal,true);para('Strict arrival AND\nno recorded contact in the episode',8.05,4.25,4.6,1.2,21);
 note('1,384 completed episodes; 1,306,599 decisions and 69,172 model queries independently checked.');
}else if(s.kind==='main_results'){
 const ms=['rpp','forecast','dwa','mppi','lattice','vlm','lora'];tx('Contact-free arrivals / 120',.6,1.93,8.6,.36,21,C.navy,true);
 bars(['RPP-inspired','Speed forecast','DWA-style','MPPI-style','Geometric','Frozen VLM','Adapted VLM'],ms.map(m=>all[m].clean),.6,2.75,8.2,120,[C.gray,C.gray,C.gray,C.gray,C.teal,C.gray,C.red],.43);
 table(['Method','Strict'],ms.map(m=>[{rpp:'RPP',forecast:'Forecast',dwa:'DWA',mppi:'MPPI',lattice:'Geometric',vlm:'Frozen',lora:'Adapted'}[m],all[m].strict+'/120']),9.25,2.07,3.45,.46,[2.1,1.35],16);
 note('A shared denominator and all seven methods: geometry 79/120, speed forecast 62/120, adapted VLM 68/120.');
}else if(s.kind==='attribution'){
 table(['Paired contrast','Contact-free difference','Travel-time difference'],[['Geometry − speed forecast','+14.17 pp\n95% CI [6.67, 21.67]','+0.45 s\n93 joint arrivals'],['Adapted VLM − geometry','−9.17 pp\n95% CI [−16.67, −2.50]','+12.23 s\n80 joint arrivals']],.55,2.03,12.2,1.02,[4.2,4.2,3.8],21);
 para('Geometry: better contact-free completion, without a speed advantage over forecasting.',.8,5.25,11.8,.7,22);
 note('Package-level geometry gain; model/rule selectors also differ in observation information. Timing excludes failures.');
}else if(s.kind==='robustness'){
 tx('Training seeds: contact-free / 120',.6,1.94,6,.4,21,C.navy,true);bars(['Seed 0','Seed 1','Seed 2'],[68,18,58],.6,2.9,5.9,120,[C.red,C.red,C.red],.64,'',19);
 tx('Input removals: contact-free / 24',7.0,1.94,5.8,.4,21,C.navy,true);bars(['Full','No RGB','No image','Minimal instr.'],[14,13,15,5],7.0,2.9,5.5,24,[C.teal,C.gray,C.gray,C.red],.56,'',18);
 tx('Geometric reference: 79/120',.7,5.28,5.8,.55,21,C.teal,true);para('No image: always centre C;\ngeometry still checks execution.',7.05,5.15,5.5,.85,19);
 note('No-image outside exposure 8.46% vs 4.68% with full input. These removals do not establish modality benefits.');
}else if(s.kind==='stress'){
 tx('Controlled blockage: contact-free / 24',.6,1.94,6.05,.45,21,C.navy,true);bars(['Geometry','MPPI-style','Adapted VLM'],[11,7,4],.6,2.95,5.9,24,[C.teal,C.gray,C.red],.65,'',19);
 tx('Curve test: contact-free / 40',7.0,1.94,5.8,.45,21,C.navy,true);bars(['Full training','Curve excluded'],[32,3],7.0,2.95,5.5,40,[C.teal,C.red],.8,'',18);
 para('Same relocated object across methods;\nreference is not replanned.',.7,5.18,5.8,.8,19);para('Training volume also changes:\n598 → 432 decisions.',7.05,5.18,5.4,.8,19);
 note('Different diagnostic suites and denominators; no claim of cross-city or real-robot transfer.');
}else if(s.kind==='video'){
 const f=s.family,p=path.join(ROOT,'research/results/videos/native_'+f+'_comparison.mp4'),poster=path.join(A,'poster_'+f+'.png'),buf=fs.readFileSync(poster),iw=buf.readUInt32BE(16),ih=buf.readUInt32BE(20),w=12.15,h=w*ih/iw,x=.6,y=2.03;
 slide.addMedia({type:'video',path:p,cover:'image/png;base64,'+buf.toString('base64'),x,y,w,h});cur.media_assets.push({family:f,path:'../../results/videos/native_'+f+'_comparison.mp4',x,y,w,h,embedded:true,poster:'poster_'+f+'.png',native_simulation:true});
 const v=data.videos.find(v=>v.family===f);const text=v.episodes.map(r=>({rpp:'RPP',lattice:'Geometry',lora:'Adapted VLM'}[r.method])+': '+(r.strict_goal?(r.any_contact?'arrival + contact':'contact-free arrival'):'timeout')+(f==='SC'&&r.method==='lattice'?' + high outside exposure':'')).join('   |   ');
 v.episodes.forEach((r,i)=>{let label=({rpp:'RPP',lattice:'Geometry',lora:'Adapted VLM'}[r.method])+': '+(r.strict_goal?(r.any_contact?'arrival + contact':'contact-free arrival'):'timeout');if(f==='SC'&&r.method==='lattice')label+='\nOutside exposure: 52.7%';tx(label,.67+i*4.05,5.57,3.9,.55,16,r.strict_goal?C.black:C.red,true);});
 note('Illustration only: seed 1502, wide band, 5 pedestrians. Native playback 2×; finished windows hold last frame.');
}else if(s.kind==='conclusion'){
 tx('SUPPORTED',.65,2.03,3.1,.42,23,C.teal,true);para('Lateral candidates and geometric constraints improve contact-free completion in this simulator.',3.9,2.02,8.4,1.03,24);
 tx('NOT ESTABLISHED',.65,3.49,3.1,.42,23,C.red,true);para('Additional navigation benefit from this single-frame, small-data VLM selector.',3.9,3.48,8.4,.98,24);
 tx('NEXT TESTS',.65,4.99,3.1,.42,23,C.navy,true);para('Temporal observations, matched supervision and broader scenes remain future work.',3.9,4.96,8.4,.93,22);
 note('No continuous-safety, pedestrian-comfort or real-city deployment guarantee. Code / data public; weights local.');
}else if(s.kind==='references'){
 const refs=['Wu et al. MetaUrban. ICLR, 2025.','Francis et al. Social robot navigation evaluation. ACM THRI, 2025.','Macenski et al. Regulated Pure Pursuit. Autonomous Robots, 2023.','Fox et al. Dynamic Window Approach. IEEE RAM, 1997.','Williams et al. Model Predictive Path Integral Control. JGCD, 2017.','Yokoyama et al. VLFM. arXiv:2312.03275.','Cheng et al. NaVILA. arXiv:2412.04453.','Sun et al. Risk-adaptive crowd navigation. arXiv:2506.14305.','Marafioti et al. SmolVLM. arXiv:2504.05299.','Hu et al. LoRA. ICLR, 2022.'];
 refs.forEach((t,i)=>tx((i+1)+'. '+t,.65+Math.floor(i/5)*6.25,2.0+(i%5)*.69,5.9,.55,16));
 tx('Code, paper, data and native videos',.65,5.78,11.8,.4,20,C.navy,true,{hyperlink:{url:'https://github.com/clzJY/INFH5000-group-assignment/tree/research/vision-language-navigation'}});
 tx('github.com/clzJY/INFH5000-group-assignment',.65,6.31,11.8,.33,18,C.teal,false,{hyperlink:{url:'https://github.com/clzJY/INFH5000-group-assignment/tree/research/vision-language-navigation'}});
}
}
for(const s of manifest.slides){for(const t of [...s.text_objects,...s.image_assets,...s.media_assets]){if(t.x<0||t.y<0||t.w<=0||t.h<=0||t.x+t.w>W+.01||t.y+t.h>H+.01)throw Error('Off-canvas '+s.number+' '+JSON.stringify(t));}}
fs.mkdirSync(OUT,{recursive:true});fs.writeFileSync(path.join(OUT,'slide_manifest.json'),JSON.stringify(manifest,null,2));
pptx.writeFile({fileName:path.join(OUT,'INFH5000_Urban_Navigation.pptx')}).then(()=>console.log('EDITABLE_MULTIMEDIA_DECK_READY',manifest.slides.length));

# Technical supplement and build instructions

## Template and reference style

The course requires the [HKUST Lab Report Template](https://www.overleaf.com/latex/templates/hkust-lab-report-template/wypwcqnrmhqj) by Ma Wanqin, licensed CC BY 4.0. The report preserves A4, 12-point body, one-inch margins, 1.5 body spacing, a cover, contents and running header. Contents, captions, tables and references use local tighter spacing for readability. The university logo was extracted from that template's PDF and retains its identity; it is used to identify the coursework, not an endorsement.

Academic organisation follows the author's EMNLP, INFOCOM, ICRA and ICLR manuscripts: explicit questions and contributions, defined interfaces and budgets, method-before-evidence ordering, grouped comparisons, readable booktabs tables, separate diagnostics and bounded conclusions. No research text, data, figures or claims from those other projects were imported. IEEE/ACL/ICLR document classes were not substituted for the mandatory course template.

## Actual model and execution

- Native environment: Python 3.11, CPU Torch 2.3.0, Panda3D 1.10.14, Shapely 2.0.6.
- Model environment: Python 3.13, CUDA Torch 2.11.0, Transformers 5.5.4.
- Backbone: SmolVLM2-500M-Video-Instruct; revision in `../protocol_model_v3.json`.
- Vision/text query/value LoRA: rank 8, alpha 16, 1,114,112 FP32 trainable parameters over a frozen bfloat16 base.
- AdamW: learning rate 0.0003, weight decay 0.01, batch size 4, ten epochs; validation-only selection.
- Three-second sampled candidates; model choice 1 Hz, native checks/actuation 10 Hz; 120 simulated seconds, target speed cap 2 m/s.
- The model sees one current RGB/map composite, not explicit velocity or temporal visual history. Teacher labels are predictive geometric choices, not counterfactual native success labels.
- New course material introduces no new training or evaluation. All numbers come from the recorded formal campaign.

## Build the report and presentation

Work from repository root. Model weights are not required for document generation.

```bash
envs/python311/bin/python3 research/course_delivery/scripts/build_report.py
cd research/course_delivery/report
pdflatex -halt-on-error INFH5000_Group_Report.tex
pdflatex -halt-on-error INFH5000_Group_Report.tex
pdflatex -halt-on-error INFH5000_Group_Report.tex
```

Use Node.js with PptxGenJS 4.0.1 (`npm install` only if unavailable) for the editable deck. The build script first resolves the module normally; it also resolves `source/node_modules`, before a local fallback reuses an already installed workspace dependency. Install the pinned dependency with `npm install --prefix research/course_delivery/source` if needed.

```bash
node research/course_delivery/scripts/build_deck.js
```

Slides read `source/slide_content.json`, `source/audited_content.json`, `source/group_metadata.json` and `assets/`. Three full native MP4s from `../results/videos/` are embedded; source paths are internal to the repository. The deck's key text, bars, numbers, tables and diagrams are native PowerPoint objects; native screenshots, the logo and video pixels remain raster/media.

Pass `--records /path/to/workspace/storage_management/OP_TIMESTAMP` to audio/video build helpers; never reuse a historical operation folder for a new run. `make_scripts_audio.py` uses the local eSpeak NG shared library for an explicitly synthetic rehearsal voice. It saves disposable audio under the timestamped workspace operation, not in the repo. `make_rehearsal.py` uses cached ImageIO FFmpeg and slide renders. No voice model or video model is downloaded. The supplied SRT is script-timed approximately, not a forced-aligned transcription.

## Preserve the scientific record

The former v12 individual proposal and seven-page research article are retained. Course-template revisions change organisation, interpretation and delivery format; they do not alter controller source, datasets, protocols or outcomes. Backbone weights and LoRA adapters remain local. Their identities and training records stay documented.

LibreOffice may copy movie streams into PDF output. The supplied slide-preview PDF was passed through Ghostscript PDFwrite with `-dPreserveAnnots=false` to retain a compact static view. Its movie poster was pixel-compared against the original render. This reduces duplicate media without rasterising the editable PPT or removing the full videos embedded in that PPT.

# INFH5000 course project delivery — review copy

This package adapts the completed navigation study to the **new group-project requirements**, not the earlier individual mini-proposal rules.

- [Course-template report, 12 pages](report/INFH5000_Group_Report.pdf) · [LaTeX source](report/INFH5000_Group_Report.tex).
- [Editable 17-slide PPT with three embedded native videos](https://github.com/clzJY/INFH5000-group-assignment/releases/download/course-review-20261121/INFH5000_Urban_Navigation.pptx).
- [Slides as PDF](presentation/INFH5000_Urban_Navigation.pdf) — movies are posters in PDF.
- [English speaker script, PDF](presentation/English_Speaker_Script.pdf) · [Markdown](presentation/English_Speaker_Script.md) · [中文逐页提示](presentation/中文逐页讲解提示.md).
- [Synthetic narrated rehearsal, MP4](https://github.com/clzJY/INFH5000-group-assignment/releases/download/course-review-20261121/INFH5000_Narrated_Rehearsal.mp4), **9 min 48 s**, including three 12-second native excerpts. Clearly marked synthetic; not a recording of the group.
- [完整审阅材料 ZIP](https://github.com/clzJY/INFH5000-group-assignment/releases/download/course-review-20261121/INFH5000_Review_Materials_20261121.zip).
- [要求审核（中文）](REQUIREMENTS_AUDIT_zh.md) · [录制与提交指南](RECORDING_GUIDE_zh.md) · [技术补充与模板来源](TECHNICAL_SUPPLEMENT.md).

## Findings retained

Geometric local selection reaches **79/120** contact-free arrivals, versus **62/120** for route-constrained speed forecasting. The primary adapted VLM reaches **68/120** and does not improve on geometry. Training-seed variation, input removals, holdout failures and unfavourable native demonstrations remain visible. All 1,384 formal results and the former v12 proposal/seven-page article are preserved. No VLM weights are included in Git, ZIP or release.

## Before formal submission

The lecture PDF requires a **4–5-person team**, no more than three from one thrust (with the stated new-RBM exception), and a title/group ID/member/work-distribution declaration at the beginning. Actual identities, thrusts and shares are unavailable, so the cover and first slide explicitly show pending fields. Fill `source/group_metadata.json`; use real work shares totalling 100%. Student IDs are not requested by this template.

Then rebuild the report/deck and run:

```bash
envs/python311/bin/python3 research/course_delivery/scripts/validate_delivery.py --require-team
```

The supplied rehearsal is a technical practice asset. Confirm course permission for narration style or record the team presentation, update its group information, and verify the final MP4 is no longer than 600 seconds. Verify the **Week 12 Wednesday 23:59:59** calendar date in Canvas. The review ZIP has no invented group ID; rename the final submission using the real ID and project name.

## Editable content and media

Main slide text, numbers, tables, bars and flow arrows are native PowerPoint objects. Simulator screenshots, the university logo and movie pixels are image/media objects. English scripts and Chinese cues are included in every slide's notes. Full native movies are embedded; separate copies are included in the review ZIP as a player fallback. The rehearsal uses short excerpts so that all 17 slides fit the time limit.

The source data are versioned in `source/audited_content.json`, with evidence links per slide in `source/slide_content.json`. The course PDF itself is retained in its original local location and is not redistributed in this package. No private data or figures from other manuscripts were imported.

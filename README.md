# INFH5000 Group Assignment

Predictive and Reactive Robot Navigation in Shared Urban Pedestrian Spaces

This repository is the starting point for the group project. It contains the completed MetaUrban pilot, its controller implementations and comparisons, recorded results, and the retained v12 proposal.

## Start here

- [Proposal with AI appendix — PDF](report/Week3_Streetscape_Research_Proposal_v12_with_AI.pdf) · [Word](report/Week3_Streetscape_Research_Proposal_v12_with_AI.docx): five-page proposal plus three-page appendix.
- [Main proposal — PDF](report/Week3_Streetscape_Research_Proposal_v12_main.pdf) · [Word](report/Week3_Streetscape_Research_Proposal_v12_main.docx).
- [Reproduction](docs/REPRODUCTION.md) and [group workflow](docs/GROUP_WORKFLOW.md).
- [Main results](outputs/classical/test/summary.csv), [paired comparisons](outputs/classical/test/paired.csv), and [controlled encounters](outputs/classical/encounter_test/summary.csv).
- [Three-dimensional comparison video](outputs/classical/videos/classical_crossing_comparison.mp4) and [inspection demonstration](outputs/classical/videos/inspection_mission.mp4).
- [Raw experiment records and checksums](https://github.com/clzJY/INFH5000-group-assignment/releases/tag/pilot-v12).

The proposal is retained as the original individual assignment. Group authorship and the next research scope can be developed separately without changing the recorded pilot.

## Completed work

The focal module predicts robot and pedestrian footprints along a reference route and selects a speed or stopping command. Comparisons include Pure Pursuit, Regulated Pure Pursuit (RPP)-inspired control, a Dynamic Window Approach (DWA)-style controller, distance-based yielding, and a zero-velocity prediction ablation. The RPP and DWA implementations are local adaptations.

The final study comprises 68 development runs, 120 matched street-scene test runs, and 40 separately reported single-pedestrian diagnostics. The final suite uses numerical simulator states and native three-dimensional physics, with no neural training or policy inference.

The measured-velocity and zero-velocity forecast variants each achieved 16/20 strict arrivals and 13/20 contact-free arrivals in the main test. Forecasting was 3.16 seconds faster than RPP-inspired control on 16 jointly successful conditions, but 0.28 seconds slower than its zero-velocity ablation on those same conditions. These results do not establish an overall advantage from measured pedestrian velocity.

A bounded local-detour trigger is proposed but has not been implemented or evaluated. It is one possible direction for the group project.

## Repository contents

| Path | Contents |
| --- | --- |
| `src/streetscape_baselines/` | Final common-input controllers, geometry and runtime |
| `src/streetscape_route/`, `src/urban_service/` | Shared tracking, simulator adapters, metrics and provenance |
| Other `src/` packages | Retained exploratory implementations |
| `scripts/`, `configs/`, `tests/` | Evaluation, acceptance checks, frozen protocols and tests |
| `third_party/` | Dependency source trees and original licenses |
| `outputs/classical/` | Final result tables, figures and videos |
| Other `outputs/` and dated technical notes | Earlier exploratory results; do not pool them with the final study |
| `report/` | v12 documents and the input records needed to rebuild them |

Raw `runs/` are distributed as release archives. Installed environments, native build products, asset bundles, download caches and personal working notes are excluded from Git. All experimental raw records are retained locally. See [third-party sources](THIRD_PARTY.md) for attribution and asset boundaries.

## Quick checks

With Python 3.11 and an isolated environment:

```bash
python -m pip install -r requirements/checks-py311.txt
PYTHONPATH=src python -m pytest -p no:cacheprovider tests -q -k 'not native_repeatability_and_zero_margin_equivalence'
```

The omitted historical CrowdNav backend test requires its native RVO2 environment. The full existing environment can run all tests. These checks do not require downloading scene assets or running a new three-dimensional campaign.

## Collaboration

Use branches and pull requests for changes. Preserve the frozen baseline and choose new output directories for new experiments. Report failures and contact outcomes alongside successful demonstrations. See [GROUP_WORKFLOW.md](docs/GROUP_WORKFLOW.md) for the proposed workflow.

The repository is private. The owner can add group members through repository settings.

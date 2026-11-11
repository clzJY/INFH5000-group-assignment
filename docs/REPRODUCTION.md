# Reproducing the pilot

Use the v12 proposal and `outputs/classical/` as the current result. Older technical notes describe the stage named in their title. The final suite has 120 street-scene tests and 40 separate encounter tests after 68 development runs.

## Code checks and existing results

Python 3.11 is the recorded interpreter series. The lightweight dependency list is `requirements/checks-py311.txt`:

```bash
python -m pip install -r requirements/checks-py311.txt
PYTHONPATH=src python -m pytest -p no:cacheprovider tests -q -k 'not native_repeatability_and_zero_margin_equivalence'
```

The full test suite also includes a historical two-dimensional CrowdNav/RVO2 integration test. It runs in the existing lab environment with `envs/python311/bin/python3 -m pytest -p no:cacheprovider tests -q`.

Read `outputs/classical/test/episodes.csv`, `summary.csv` and `paired.csv`, and the corresponding files under `encounter_test/`. The separate diagnostics must not be pooled with the main test.

## Raw records

Download the `pilot-v12` release archives and their SHA256 file from this repository. Verify the downloaded checksums, then extract the archives in the repository root. `pilot-evidence.tar.gz` contains the final study's development/test campaigns, recording runs and related diagnostic gates. `historical-evidence.tar.gz` contains earlier experiments. Archives preserve regular files under their original `runs/` paths; machine-specific simulator symlinks and Python bytecode are omitted.

The acceptance script replays controller decisions and recomputes metrics from JSONL, without starting a new simulator:

```bash
mkdir -p build/acceptance
PYTHONPATH=src python scripts/accept_classical.py runs/classical_test_20261102 \
  --record build/acceptance/main.json --output build/acceptance/main_tables
PYTHONPATH=src python scripts/accept_classical.py runs/classical_encounter_test_20261102 \
  --record build/acceptance/encounters.json --output build/acceptance/encounter_tables
```

These commands require NumPy and unchanged frozen source files. They deliberately reject source changes. For new controller research, preserve the old results and create a new development/frozen protocol.

## Rebuild the document

The report's numerical audit and dialogue inputs are in `report/source/`; the figures and screenshots referenced by the builder are committed. With Pillow installed:

```bash
python scripts/build_proposal_v12.py --operation report/source \
  --output build/proposal/Week3_Streetscape_Research_Proposal_v12_with_AI.docx \
  --include-ai-appendix
libreoffice --headless --convert-to pdf --outdir build/proposal \
  build/proposal/Week3_Streetscape_Research_Proposal_v12_with_AI.docx
```

Choose a new output directory when rebuilding; the builder protects existing Word files. LibreOffice and suitable serif/CJK fonts are required for comparable PDF layout. The delivered PDF is the retained layout reference. The appended conversation includes original file links from that conversation; those refer to historical deliveries rather than current repository files.

## Native simulation environment

The final pilot ran on Linux x86_64 with CPython 3.11.14, NumPy 1.26.4, Panda3D 1.10.14, Gymnasium 0.28.1 and the pinned MetaUrban source in `third_party/`. The complete runtime versions are listed in `requirements/runtime-linux-py311.txt`. The pre-existing Linux environment and downloaded wheelhouse remain on the lab server and are not committed.

For an offline installation, obtain the verified `mac_artifacts` bundle from the project owner, place it under `cache/mac_artifacts/`, then run:

```bash
bash scripts/setup_offline.sh "$PWD/cache/mac_artifacts"
```

This installs the local Python environment and builds the native ORCA extension. It needs an existing C++ compiler and CMake. `scripts/download_on_mac.py --stage list` lists the original upstream acquisition sources. The bundled receipts, tiny scene assets and native pedestrian archive are required for the asset-import step; they are distributed separately from this repository. The large full-static archive is not needed by the final tiny-scene study.

The final asset profile combines `assets_tiny.zip` and native glTF models extracted from `assets_pedestrain.zip`. The hashes recorded for the pilot are:

```text
assets_tiny.zip        3a2eedb116ac37359d6fd295e5a8ab8af926acfe64b4517986d86c0922de3ce6
assets_pedestrain.zip  50fe37fb1440582a0fb715159402f514ef18d643a669c69c5b82621fad64e3e8
```

These are recorded transfer hashes, not independently published upstream hashes. On the lab server, reuse the installed assets and environment. For a new machine, set `INFH_RECORDS_DIR` to a new, persistent absolute directory for import receipts (on this lab workspace, use its central `storage_management/` directory), then run:

```bash
mkdir -p "$INFH_RECORDS_DIR" outputs/preparation
printf '%s\n' "$INFH_RECORDS_DIR" > outputs/preparation/current_execution_record.txt
envs/python311/bin/python3 scripts/import_streetscape_assets.py
```

The importer verifies receipt coverage and refuses unsafe/encrypted members and conflicting asset links. Keep the receipt directory: the imported profile links to it. Simulator rendering additionally requires a suitable OpenGL/EGL setup. The inherited validator checks a small pretrained checkpoint, but the final classical suite does not execute it.

## New campaigns

Use separate new output and log directories. On the lab server, follow its Slurm rules for long runs and GPU rendering. The following commands assume the native environment, assets and ORCA build have been prepared:

```bash
envs/python311/bin/python3 scripts/evaluate_classical.py \
  --config configs/classical_frozen_20261102.json --split test \
  --campaign runs/NEW_classical_test --log-root "$INFH_RECORDS_DIR/logs" --workers 2
envs/python311/bin/python3 scripts/evaluate_classical_encounters.py \
  --config configs/classical_frozen_20261102.json --split test \
  --campaign runs/NEW_classical_encounters --log-root "$INFH_RECORDS_DIR/logs" --workers 2
```

These reproduce the frozen protocol; they do not implement the proposed detour extension. See `docs/Week3_v5_Reproducibility_Note.txt` for metric definitions and `docs/classical_reproduction_20261102.txt` for the original technical record.

# Third-party sources

The source trees used locally are included so that the project-specific adapters can be inspected together with their dependencies. Original licenses remain in their directories. Native build outputs and downloaded scene/pedestrian asset bundles are excluded.

| Component | Source/version used | License file |
| --- | --- | --- |
| MetaUrban | `metadriverse/metaurban`, commit `6b8ff9aa48dd27d5c57fa1c712db520732f11fa9` | `third_party/metaurban/LICENSE.txt` |
| CrowdNav, historical 2D experiments | archived source `CrowdNav-20d67808.tar.gz` | `third_party/CrowdNav/LICENSE` |
| Python-RVO2, historical 2D experiments | archived source `Python-RVO2-c2c46ba8.tar.gz` | `third_party/Python-RVO2/LICENSE` |

MetaUrban's local ORCA CMake adaptation uses the installed pybind11 package; see `scripts/prepare_orca_build.py`. The small pretrained policy is retained because the inherited input validator checks its hash, although the final classical-controller suite does not load it or perform neural inference. Optional upstream downstream-task submodules are not populated by this project.

Scene and pedestrian assets must be acquired through their upstream distribution and applicable terms. `scripts/download_on_mac.py` records the asset URLs used for the pilot. Download receipts and local native builds are not Python source dependencies and are not committed as installed environments.

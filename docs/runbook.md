# 从离线准备到真实评测

当前阶段只准备本地文件。下列仿真命令尚未执行，必须在 Mac 下载物回传后按顺序运行；不需要先开启星流。

## 实验室服务器离线安装

工作目录为 `/data/private/user7/projects/Tempfile/UCMP-MB/week3_assignment`。Mac 回传路径按下载说明设为 `cache/mac_artifacts/`。安装工具只读这些下载物，`pip` 使用 `--no-index`，不修改 Conda base 或 Week 2 环境。

```bash
cd /data/private/user7/projects/Tempfile/UCMP-MB/week3_assignment
bash scripts/setup_offline.sh "$PWD/cache/mac_artifacts"
```

安装产物是项目内 `envs/python311/`。源码 checkpoint 记录的原环境为 Python 3.9.19、SB3 2.3.2、PyTorch 2.3.0、Gymnasium 0.28.1；本项目保持后面三者的主要版本并采用 Linux CPython 3.11.14。这个适配需要离线导入和真实仿真验收，不视为完全复刻原环境。

ORCA 编译使用外部 pybind11 2.13.6，避免旧 vendored 头文件与 Python 3.11 的兼容问题。`prepare_orca_build.py` 只替换 CMake 中两行 pybind11 选择逻辑，原始源码压缩包仍保留。构建并行数为 2，不使用全部可见 CPU。

要求输出 `OFFLINE_IMPORTS_PASSED` 与 `OFFLINE_ENVIRONMENT_READY_SIMULATOR_GATE_PENDING`。若 pip、CMake 或 import 出错，先修复该阶段，不能把失败环境推进到仿真。

## 导入完整资产

```bash
envs/python311/bin/python3 scripts/import_assets.py "$PWD/cache/mac_artifacts" --profile full
envs/python311/bin/python3 scripts/preflight.py
```

导入时输入官方解压码。脚本核对传输 receipt，解压到新的 `assets/full/`，再关联上游需要的 `assets` 与 `assets_pedestrain` 路径。任何已有资产目录／链接都不会被覆盖。若先导入 tiny，再切换 full，需要明确选择新配置与链接处理方式，不自动移除 tiny。

`preflight` 返回 0 才表示运行输入齐备；返回 2 会列出缺项。它只做只读检查，不下载、不初始化仿真、不申请 GPU。环境依赖锁定由 Mac wheel receipt 和安装后的实际版本共同记录。

## 第一条真实 baseline 视频

先检查本人任务和 GPU 使用，再用一张 RTX 5880 申请短交互任务。以下在实验室服务器终端运行：

```bash
squeue -u "$USER"
nvidia-smi
srun --partition=staff --gres=gpu:staff:1 --cpus-per-task=8 --mem=24G --time=00:30:00 --pty bash
```

进入分配的 shell 后，切换项目目录并运行：

```bash
cd /data/private/user7/projects/Tempfile/UCMP-MB/week3_assignment
envs/python311/bin/python3 scripts/run_episode.py --config configs/baseline_static.json --seed 20 --method baseline --record --output runs/baseline_first
```

产物包括 `rollout.mp4`、`steps.jsonl`、`summary.json` 和原始配置。输出目录必须是新路径。`status=complete` 表示该次执行正常结束，导航是否成功查看 `navigation_success`，两者不要混淆。正式评测统一采用确定性推理；原示例默认随机采样，这一差异记录在方法中。

若离屏渲染失败，先查看错误日志和当前驱动图形能力。官方 FAQ 的引擎 warmup 可作为后续兼容性修复；Xvfb 也需检查是否误用软件渲染，不能只以能导出一张图片判定 GPU 图形路径已验证。不要修改 Slurm 设置的 `CUDA_VISIBLE_DEVICES`。

## 有限验收、开发与冻结

在同一个已分配的 GPU shell 中：

```bash
envs/python311/bin/python3 scripts/simulator_gate.py --output runs/gate_first
envs/python311/bin/python3 scripts/evaluate.py --split development --campaign runs/development_first
```

有限验收包括两个同条件原策略 episode、一个修改策略 episode、两段视频解码和独立的实际加速／制动检查。每段策略运行最多 80 步，制动检查最多 60 步。记录与不记录视频的轨迹必须在五位小数精度内一致；失败时分析原因，不自动放宽阈值。该验收不要求声称研究改进。

用开发集检查失败原因、是否存在行人交互、限速和滞回是否有效；只在开发配置中修改参数。完成修改后，对最终配置重新运行 gate，再冻结：

```bash
envs/python311/bin/python3 scripts/freeze_protocol.py --gate runs/gate_first/gate_report.json --output configs/evaluation_frozen.json
```

脚本要求 gate 绑定当前开发配置的哈希，否则拒绝冻结。冻结路径必须是新文件。开发结果和 gate 不是正式测试结果。

## 正式测试与图表

回到实验室登录 shell，在项目目录提交：

```bash
sbatch scripts/evaluate.slurm configs/evaluation_frozen.json
```

调度脚本只申请一张 GPU、8 CPU、24 GB 内存、最多 2 小时。若初始测速表明需要更久，再按实测调整，不同时启动重复任务。每次 campaign 生成新的时间戳目录；一个环境进程结束后再启动下一个。

评测会核对完整配对、初始场景、核心代码、资产、checkpoint、软件版本一致性，输出 `episodes.csv`、`grouped_results.json` 和 `paired_differences.json`。环境或软件异常立即停止并保留已有条件。最终绘图：

```bash
envs/python311/bin/python3 scripts/make_figures.py runs/实际的campaign目录
```

正式测试默认只在完成巡检时保存一帧，减少视频开销。展示视频对预先指定的同场景三方法单独使用 `run_episode.py --record` 重跑，保留其正式协议与种子，不将重跑 episode 重复计入统计。

## 未来移交星流

当前不调用控制台、不建立 SSH 连接、不启动实例。准备文件、下载和校验不需要 GPU；如果未来已有用户指定的保留资源，可以继续使用，无需为本项目另开实例。

候选持久化根目录是 `/mnt/data/clzjy/ucmp-week3-urban-nav/`，其中源码放入新的 release，场景和环境位于该项目的持久化资产区域，运行写入独立 runs。避免把下载物和环境放到容器 `/root`。

需要启动时，再按 `xingliu-platform-operations` 最新注册表和已验证 SSH profile 核对 console endpoint、host key、hostname 与 GPU UUID，不把当前／历史 IP 固化到本项目。

推荐先 1 GPU、8 vCPU、24–32 GiB RAM、KPFS、SSH；先验证 GPU 图形驱动／离屏渲染能力再选具体卡型。A800 显存多不代表此类仿真一定比 RTX 5880 更合适。若本地有限验收和 60 个 episode 的耗时可接受，可以全程使用本地单张 5880。

在云端仍按同样顺序完成离线安装、有限 gate、开发、协议冻结与评测。公开资源继续由 Mac 获取，云端不自动下载。迁移时在云端重新导入资产，不能把指向实验室绝对路径的符号链接原样复制后当作有效资产。

> 状态修正：本文记录此前二维辅助路线，并非三维街景任务最终完成。当前主线见 [三维修正](streetscape_revision.md)；GenAI 部分已按用户要求推迟。

# 最终技术说明与完整复现流程

执行日期：2026-11-02。当前报告采用 CrowdNav；早期 `experiment_protocol.md`、`runbook.md` 与 MetaUrban 配置是保留的准备路线，不能用于解释最终实验。最终权威输入为 `configs/crowd_clearance_frozen_20261102.json` 和测试 campaign 的 `protocol.json`。

## 实际任务与资源选择

机器人从 (0,−4) m 穿越 5 个动态行人，到达 (0,4) m 的巡检 waypoint。保留官方 CrowdSim 的 reset、step、场景生成、碰撞、到达和超时规则。任务止于到达；没有实现巡检照片、机械臂、双足行走或 VLA。图中的方格是坐标参考，环境没有实体墙体。视频是实际闭环状态轨迹的可视化，不是三维摄影级街景。

MetaUrban 完整静态包仍需官方密码；tiny 包不加密但服务器实测约 0.58–0.69 MB/s，未继续下载。原交付资源全部保留。公开 CrowdNav 源码仅 27 KB，RVO2 源码约 175 KB；新增 Cython wheel 约 3.6 MB，实测 1.91 MB/s。下载和哈希记录集中保存。主实验不需要大型场景资产，也不需要 GPU 或星流。

## 准确版本与模块实现

- Linux x86_64；项目隔离 CPython 3.11.14；NumPy 1.26.4、Gymnasium 0.28.1、Matplotlib 3.9.4、Pillow 11.0.0、ImageIO 2.36.1 / FFmpeg wheel 0.5.1。
- CrowdNav：`20d678085c06831e658a65b9e20c8bb6f6ecdc10`，官方 https://github.com/vita-epfl/CrowdNav 。使用 CrowdSim 和 ORCA，不使用论文的 SARL 网络或权重。
- Python-RVO2：`c2c46ba8d59556aa10faf03479293236efea154d`，https://github.com/sybrenstuvel/Python-RVO2 。使用 Cython 3.0.12 构建，本机 CPython 3.11 wheel 保存在 `cache/fallback_wheels/`。
- 兼容桥只将旧 Gym 的导入名映射到 Gymnasium，然后直接实例化官方 CrowdSim；没有改写原有 step、返回值或场景生成。
- 原始 ORCA 无修改。两种模块在机器人 ORCA 优化时将每个代理的规划半径加 b；物理碰撞半径仍是 0.30 m。原生 0.01 m 余量保留。固定 b=0.15 m；自适应 b∈[0,0.15] m，2 s 预测，0.60 m 触发，0.15 m/s 释放。每步重建规划器使新半径生效。
- 自适应预测用直指目标的期望速度与行人当前速度计算最小边界间距 d*；目标 b=0.15×clip((0.60−d*)/0.60,0,1)。两方法都直接执行优化后的速度。0.15 m 不是实测最小通行间距。
- 完整安装清单和下载 receipts 在中央记录；现有环境还包含 MetaUrban 和 CPU Torch，但最终路线不训练或调用神经网络，也不依赖城市资产。

## 开发失败与冻结

最初在求解后的速度向量上限速；在 `runs/crowd_development_v1/` 的 30 次开发测试中，修改常常增加碰撞。限速并不自动保持 ORCA 已求解的避碰条件，行人也不会对机器人主动让行。该路线保留为失败记录。

随后仅在开发 case 900–904 上评估一个间距候选，见 `runs/crowd_clearance_development_v1/`（另 30 次）。2026-11-02 00:26 冻结后运行测试 case 100–109；它们由原生 `reset('test', case)` 映射到 RNG seed 1100–1109。两类场景复用 case ID，配对单位是 `(scenario, case_id)`，不是 60 个独立场景。

冻结运行源 SHA256：`a9fa1955362084b61daa3e308bad48dd941de0c74efc84051961517a7d595117`。测试入口会验证该 hash；修改源代码需要新协议，不能覆盖现有结果。

## 指标、结果与数值问题

原生成功/碰撞/超时与独立几何检查同时保存。最小间距沿每步真实相对线性运动解析计算；小于 0.20 m 的暴露时间取多个行人事件的并集，避免重复计时。近距离比例先按各 episode 计算，再对 20 个 episode 求均值，分母是该 episode 终止时长。碰撞提前终止会截短暴露，因此结果必须同时阅读终止类型。物理重叠与原生碰撞在这 60 次中完全一致。

固定缓冲 20/20 到达；原始策略 12/20；预测缓冲 18/20。预测方法两次碰撞，不能称它全面优于固定方法。相同 12 个共同成功场景上，固定增加 0.875 s，预测增加 0.5625 s。这是有条件的时间比较，不把碰撞终止当作快到达。

`robot.visible=false` 是官方默认：行人彼此用 ORCA，但不观察机器人。这提供可重复的非合作压力测试，也破坏 ORCA 互相承担避碰责任的条件；不能据此声称理论保证。所有方法初始状态相同，行人轨迹在共同前缀逐步完全一致。

独立验收中，原先用 1.0000001 m/s 作严格诊断界限失败，因为原生 RVO2 浮点求解产生最高 **1.0001193437654947 m/s**。没有截断动作或修改已有轨迹。最终验收记录实际数值，并检查有限性、位移一致性和小数值容差。27 项单元/集成测试通过，另核对 60 个 episode、20 个匹配初始状态、2,307 步真实动作和 613 个相同行人轨迹前缀时间步。

## 本地重复执行

从本目录执行；现有隔离环境已可用。不要覆盖已有 run 目录，测试入口会拒绝覆盖。

```bash
envs/python311/bin/python3 -m unittest discover -s tests -v
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 envs/python311/bin/python3 scripts/run_crowd.py \
  --config configs/crowd_clearance_frozen_20261102.json --split test \
  --output runs/crowd_test_reproduction_20261102
envs/python311/bin/python3 scripts/crowd_outputs.py \
  --campaign runs/crowd_test_reproduction_20261102
envs/python311/bin/python3 scripts/build_proposal.py
libreoffice --headless --convert-to pdf --outdir report report/Week3_Mini_Research_Proposal.docx
```

后两个绘图/排版命令更新当前展示文件，原始冻结日志不会覆盖。只检查本次结果时无需重跑，直接读 CSV 和日志即可。墙钟时间会不同，确定性轨迹 hash 和实质指标应一致。

迁到新的 Linux x86_64 主机时，复制项目源文件、`third_party/CrowdNav`、`cache/fallback_wheels` 和既有 `cache/mac_artifacts`。执行 `bash scripts/setup_crowd_offline.sh /absolute/path/to/mac_artifacts`。这个简化安装器不联网、不安装 MetaUrban，只用既有 Mac wheel 和已构建 RVO2 wheel；跨发行版/架构如不兼容应从保留的 RVO2 源码重新构建。最终项目已安装，当前无需再运行安装器。

主测试 Slurm job 12392 因目标节点 DOWN/DRAINED 未启动；核实为本人作业后取消。随后以单线程 CPU 执行不到一秒的主仿真，未重复派发、未占用 GPU。视频渲染另需短时间 CPU。后续扩展应使用实验室可用调度资源。

独立复现还新建了 `envs/crowd_verify`：只从 Mac wheelhouse 离线安装上述最小依赖与本机 RVO2 wheel，通过 27 项测试，重跑到 `runs/crowd_independent_reproduction_20261102/`。60 个 `steps.jsonl` 与首次运行逐字节一致，除墙钟耗时外所有 summary 字段相同。这是重复相同测试案例，不增加统计样本数。说明该路线无需 MetaUrban 或 Torch；中央 `independent_reproduction.json` 保存验收结论。

## 视频、报告与提交

`comparison_circle_100.mp4`、`comparison_square_100.mp4`：预先指定各类最低测试 ID 的对比。`failure_circle_105.mp4`：因预测方法失败而选的补充案例，非代表性挑选。单独的 `baseline_circle_100.mp4`、`fixed_buffer_circle_100.mp4`、`predictive_buffer_circle_100.mp4` 从同一对比视频逐面板提取。视频用原生日志的 0.25 s 分段线性运动插值至 12 fps，终止后保持最终画面并标注；没有额外生成行为。

正文 4 页含图和参考文献，AI 附录另附。姓名/学号没有可核实来源，未编造身份。AI 截图实际拍摄本地文本编辑器中的原始聊天导出摘录和生成输出，附录明确说明并非原 ChatGPT 网页截图。正式提交正文及 AI 附录，CSV/视频可作为补充。早期准备文档仅供历史追溯。

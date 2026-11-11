# 最终三维实验：技术说明与复现

本文件记录 2026-11-02 完成的官方 MetaUrban 三维街景主线。旧 CrowdNav 目录是二维辅助实验，不是本文件指标或视频的来源。GenAI 部分按用户指示留待后续，不包含在本轮正文或交付包中。

## 实际任务和证据

使用原生 X 型交叉路口、道路、人行道、斑马线、街道物体、动态行人和 Bullet 物理。轮椅外观机器人以官方 PointNav PPO 权重逐步读取 271 维 state/LiDAR 观察，输出转向、油门/制动动作。摄像头只负责记录，不参与策略决策。不是二维轨迹贴街景背景，也不是人形全身控制或 VLA。

目标为原生导航路线的终点；原生到达主要使用路线完成度 >95%（上游另有极短路线分支）。导航统计截止到原生终止，不能将到达自动视为无接触、安全停车或完成实际物体检查。第一视角成功运行另保留终点视图。若输出有独立停车/检查阶段，该阶段与导航指标分开记录。

## 软件、资产与适配

- MetaUrban 固定 commit `6b8ff9aa48dd27d5c57fa1c712db520732f11fa9`。
- 官方 `pretrained_policy_576k.zip` SHA256 `fc0e86321d7c790b2ff547f79e58da253d589e066597864072ab2c1b8beedd99`。权重不变，无训练或微调。
- CPython 3.11.14、Torch 2.3.0+cpu、SB3 2.3.2、Gymnasium 0.28.1、NumPy 1.26.4、Panda3D 1.10.14；推理使用 CPU。已编译原生 ORCA 扩展，Python 3.11 构建兼容处理保留在旧准备记录中。
- 公开 tiny ZIP：479067250 字节，304 条目，261 个文件，零加密；实际 SHA256 `3a2eedb116ac37359d6fd295e5a8ab8af926acfe64b4517986d86c0922de3ce6`。这不是官方独立发布的 hash；Mac/服务器传输校验一致且 ZIP CRC 通过。
- 原行人包离线导入 72 个原生 glTF 模型和动作，不提取无关打包视频或辅助文件。tiny 和行人完整原压缩包、原 receipts 均保留。
- `assets/streetscape_tiny_20261102/` 保存解压资产；上游预期路径通过明确的项目内链接提供。资产 receipt 保存中央记录，项目 profile 仅引用记录。
- 无显示器渲染使用原生 EGL / `p3headlessgl`。浮点渲染目标关闭上游 16× MSAA；阴影深度改为 24 bit；关闭渲染多线程。这些只调整图像缓冲，不改场景几何或物理。
- 上游部分行人路径以工作目录解析 `./metaurban`；每次 run 建立到固定源码目录的链接，使资产路径正确，并把规划临时文件留在对应 run 内。
- tiny 示例需要显式配置 `show_ego_navigation=false`。上游静态对象管理器不支持密度恰为 0；制动验收使用 0.01，正式场景使用 0.3。

## 小模块与控制边界

三种方法为原 PPO、距离让行、预测让行。正式实验三者统一关闭倒车：这是相对官方手动演示的动作契约限制，报告将其明确列为迁移实验边界，不能把这些结果当成原始完整配置的公开 benchmark 分数。

距离模式按当前代理间距触发；预测模式以 2 s 匀速最近接近估计触发，附加 0.25 m 释放余量、0.5 s 持续解除条件和 1 m/s² 限速恢复。间距在 0.5–1.5 m 之间时，目标速度上限在 0–2 m/s 间变化。PASS 完全传递原动作；实际速度受物理制动滞后影响，不是强制截成上限。转向由 PPO 保持。

开发中发现原生负油门在接近静止时会轻微倒溜。最终模块在 WAIT 且速度 <0.5 m/s 时保持有限的原生最大轮刹车力，并清除发动机力；没有修改位置或强制清零速度。距离和预测模式共享该保持逻辑，基线导航阶段不启用。真实制动验收验证加速后能减至 <0.1 m/s，并且未明显倒溜。先前失败记录完整保留。

## 配对、冻结和指标

开发 seed 900–901，每档 5/15 人三方法共 12 条最终开发 rollout。此前不含制动保持的 12 条开发结果也保留。测试 seed 100–109，与开发分离。最终共 3×2×10=60 条测试，20 个匹配条件，每方法 20 条。先通过实际仿真验收，再冻结 `configs/streetscape_frozen_20261102.json` 中的参数和源文件 hash；测试入口每个子进程前后检查冻结源码。

配对验证同一初始几何和原生规划路线。背景行人由原生 ORCA 路径生成及激活逻辑驱动，不等同真实人的交互回应。固定权重、原生场景、目标和初始状态保持一致；不同方法之后的机器人轨迹可以不同。相同 seed 在两档人数下是两个条件，不是 60 个独立场景，也不是多次训练得到的均值。

间距代理：ego 外接圆半径 0.9013878 m，行人使用上游声明 RADIUS=0.35 m；并非所有物理碰撞体的外包络或精确表面距离。近距离指标在每个 0.1 s 决策后采样，阈值 1 m，先按 episode 计算比例再求平均；不能将负代理间距直接当成原生碰撞，或将该指标解释为人的舒适度。

上游 SimplePedestrian 的 Bullet chassis 标记为 VEHICLE。因此在本次已关闭其他移动交通的场景中，行人接触取原生 `crash_human OR crash_vehicle`，原始两项标志仍记录。此映射禁止用于混合交通条件。`any_collision` 还累计静态物体、建筑、边界等标志；成功与无接触成功分开。边界标志在运行时累计，但不在逐步 raw info 子集内，独立重算不会伪称核对了缺失的每步边界标志。

超时/接触不当作软件错误，不排除失败 episode。时间差只在同一批共同成功条件上比较，不能用较早失败冒充高效率。具体结果见 `outputs/streetscape/tables/summary.csv` 和英文正文。

## 最终结果与数据质量复核

| 方法 | 原生到达 /20 | 行人接触 /20 | 无任何接触到达 /20 | 平均近距离时间比例 |
|---|---:|---:|---:|---:|
| PPO baseline | 8 | 4 | 6 | 1.13% |
| Distance yield | 7 | 4 | 6 | 2.17% |
| Predictive yield | 8 | 3 | 6 | 1.24% |

不能将预测方法称为整体更好：只少了一个行人接触 episode，到达数及无接触到达数没有提高，近距离暴露未低于基线。两种模块分别在 7/20 和 8/20 个场景实际改变动作或请求保持制动。

独立复核发现 seed101 在两档人数下的规划起终点同为 (211,28) m，原生短路线分支在一个决策后返回成功。保留全部 60 条原始结果，另作明确标为事后数据质量检查的敏感性分析：对所有方法同时去掉这两个匹配条件后，正常到达数依次为 6/18、5/18、6/18，行人接触为 4/18、4/18、3/18。不能将这六条一步成功包装为有意义的导航。

去掉这两个退化条件后，三方法共同完成的 5 个正常场景中，距离让行相对基线平均耗时变化 −0.10 s，预测让行为 +3.06 s。该条件时间比较不涵盖“是否到达”发生变化的场景，不能作为总体效率排名。

`scripts/accept_streetscape.py` 独立重算 60 条记录中的 20,324 个决策步，验证路径长度、采样间距/暴露、等待、接触归因、goal 标志和冻结源 hash。20 个匹配条件的行人轨迹在共同前缀上完全一致（最大位置差 0 m）。该现象只描述本轮原生仿真，不代表行人能真实理解机器人。

另行选择低人数 seed100 距离策略做能力演示：导航 24.7 s、未发生接触，到达后在 1.3 s 的额外阶段中连续保持 <0.1 m/s 满 1 s，并保存现场图片。该阶段不加入导航时间，不增加正式样本数。`scripts/record_inspection_pan.py` 仅在停稳后将记录相机每帧转 30°、最大转 90°，记录侧向街景；相机不是策略输入，控制实现保持冻结。

## 复现命令

现有环境与资产已就绪，不需要下载、不需要星流。输出目录须为新目录；不要覆盖原实验。

```bash
envs/python311/bin/python3 -m unittest discover -s tests -v
envs/python311/bin/python3 scripts/evaluate.py \
  --config configs/streetscape_frozen_20261102.json --split test --workers 2 \
  --campaign runs/streetscape_test_reproduction_NEW \
  --log-root /data/private/user7/projects/storage_management/NEW_TIMESTAMPED_OPERATION
envs/python311/bin/python3 scripts/accept_streetscape.py runs/streetscape_test_reproduction_NEW \
  --output /data/private/user7/projects/storage_management/NEW_TIMESTAMPED_OPERATION/acceptance.json
envs/python311/bin/python3 scripts/streetscape_outputs.py runs/streetscape_test_reproduction_NEW
```

复现会产生新日志，已有冻结结果保留。两个 worker 只用于无图像的原生物理评测；录视频使用 `scripts/run_episode.py --record`。本轮 Slurm 节点处于 DRAIN，因此在已授权本地服务器直接使用两个有界 CPU worker，渲染使用本地 5880；没有启动星流、训练或重复 Slurm 作业。

`scripts/record_streetscape_demos.py` 重录预先指定最低测试 seed100 的三种方法；这些 RGB 重复不增加正式测试样本数。另有开发 seed900 的距离让行成功示例及其基线对照，明确标为开发示例。视频合成只叠加真实日志状态，终止后保持最终画面时显式标注，不把静帧伪装为机器人仍在运行。

## 报告和范围

最终英文正文为 `report/Week3_Streetscape_Research_Proposal.docx/.pdf`，3–5 页内含真实街景图、量化结果及参考文献。只有这个三维主线的结果作为当前主证据。旧二维报告保留历史，不与三维统计合并。GenAI 部分推迟；未伪造姓名、学号、实际城市采样或成功率。

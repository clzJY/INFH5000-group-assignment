# MetaUrban 源码核查

核查日期为 2026-11-01。上游固定为 commit `6b8ff9aa48dd27d5c57fa1c712db520732f11fa9`。本地只获取源码与其中已有 checkpoint，没有运行仿真。

## 策略与环境

[官方预训练示例](https://github.com/metadriverse/metaurban/blob/6b8ff9aa48dd27d5c57fa1c712db520732f11fa9/metaurban/examples/drive_with_pretrained_policy.py) 使用 `SidewalkStaticMetaUrbanEnv`、`agent_type=wheelchair`、271 维状态／LiDAR 输入、两维动作及 PPO MLP。它不是视觉语言策略。动态环境存在单独的 [示例](https://github.com/metadriverse/metaurban/blob/6b8ff9aa48dd27d5c57fa1c712db520732f11fa9/metaurban/examples/drive_in_dynamic_env.py)。公开树包含 SocialNav 训练入口，但没有对应的 SocialNav `eval_ppo.py`，不能把目录名称当作 checkpoint 来源证明。

checkpoint 为 655,890 字节，SHA256 `fc0e86321d7c790b2ff547f79e58da253d589e066597864072ab2c1b8beedd99`，Git blob SHA1 `37c861a38695f9902fc9bf7d851d7e7160709b13` 已与官方 tree 对照。只读取 ZIP 内文本元数据，未反序列化模型：原保存版本 SB3 2.3.2、Python 3.9.19、PyTorch 2.3.0+cu121，保存时 GPU Enabled=False，Gymnasium 0.28.1、NumPy 1.23.5。

运行入口使用同构 PPO 加载参数，保持 checkpoint 不变；动态迁移是否有效以及到达率如何，仍需实测。原示例的 `manual_control=True` 改为 false，以保证动作实际由策略提供；确定性推理、无显示器渲染和记录代码为复现适配，须在报告中说明。

## 动作和速度

`WheelchairAgentManager` 创建 `EgoWheelchair`，其继承 `EgoDeliveryRobot`，使用轮式转向与油门／制动控制。负纵向动作在开启倒车时可能变成倒车；动态对照统一关闭倒车，并安排实际制动 gate。

背景角色的实现不同。`humanoid_manager.py` 先通过 ORCA 生成轨迹，再在 `after_step` 逐步设置其位置；部分背景角色速度属性含近似或不可靠实现。本项目据相邻决策帧位置和实际 dt 计算速度，避免使用错误的二维速度向量或错误的步长倍数。

## 资产与图形

[官方拉取代码](https://github.com/metadriverse/metaurban/blob/6b8ff9aa48dd27d5c57fa1c712db520732f11fa9/metaurban/pull_asset.py) 的 tiny 路径仅下载静态资产包。完整路径分别获取静态和行人包，静态包需要注册密码。上游实际目录为 `assets_pedestrain`，保留拼写。

原引擎缺失或发现旧资产时会自动下载。本项目运行适配将该行为替换为清晰报错；只有 Mac 下载器负责完整资产获取。离线渲染按 [官方 FAQ](https://github.com/metadriverse/metaurban/blob/6b8ff9aa48dd27d5c57fa1c712db520732f11fa9/documentation/FAQs.md) 准备，但仍需 GPU 验收。

## 本地硬件

Ubuntu 24.04.3 LTS、Linux x86_64，8 张 NVIDIA RTX 5880 Ada Generation，每张显存 49,140 MiB，驱动 595.58.03。已存在 Conda、Xvfb、cmake、make、gcc 与 Slurm；当前 base Python 3.13.12、NumPy 2.5.3 不适合直接运行上游，故使用项目内独立 Python 3.11。未向既有环境安装任何包。

## 参考研究入口

- [MetaUrban](https://arxiv.org/abs/2407.08725)：城市仿真与导航任务。
- [社会导航评测原则](https://arxiv.org/abs/2306.16740)：安全、效率与社会行为的多维评测。
- [ORCA](https://gamma.cs.unc.edu/ORCA/)：背景多代理轨迹机制的理论参考。

本次实现属于已有导航策略上的轻量规则适配，算法新颖性有限。Proposal 的证据价值来自可复现的城市条件对照、失败分析以及安全／效率权衡，不能由此宣称完整人形控制、视觉感知或真实城市安全。

# 三维街景目标修正

用户于 2026-11-02 明确指出：二维图示不满足城市街景目标，GenAI 部分后续单独处理。之前 CrowdNav 的 60 次测试仅作为辅助方法研究，不能再称为本任务最终完成。

本轮不再以其他二维渲染替代。正式主线恢复官方 MetaUrban：真实道路/人行道/路缘/场景物体、原生 Bullet 物理和 RGB 相机；官方 PPO 在每一步读取实际观察并产生动作。视频先验收场景和运动真实性，再运行小模块对照。具体支持哪些建筑类型以 tiny 实际加载结果为准，不能预先声称拥有完整城市资产。

## 当前已验证

- 隔离环境 CPython 3.11.14、Panda3D 1.10.14、SB3 2.3.2、CPU Torch 2.3.0 和编译 ORCA 仍在，原 checkpoint hash 保持。
- 2026-11-02 实际运行 `p3headlessgl` 离屏渲染，640×360 图像输出成功；驱动报告 NVIDIA RTX 5880 / NVIDIA 595.58.03。此为引擎检查，不是街景 rollout，未冒充实验成果。
- 原生行人包已在服务器，无加密；已离线导入 72 个原生 glTF 模型及动作文件。加密完整静态包及所有历史资源保留。
- 公开 tiny 包共 479067250 字节、304 条目、零加密。服务器重新进行 8 路有界读取共 16 MiB，实测 0.533 MB/s，仍低于用户允许服务器执行下载的 1 MB/s 条件，因此没有下载整个包。

唯一需 Mac 补充的文件是 `assets_tiny.zip`。完整可直接转交 Mac 的指令见 `mac_tiny_asset_prompt.txt`；不重下已有资源、不等注册密码。

## 文件到位后的执行顺序

1. `envs/python311/bin/python3 scripts/import_streetscape_assets.py`，离线导入 tiny；已有行人模型准备结果复用，不覆盖资产。receipt 放中央修正记录，项目内仅有指向记录的引用。
2. 先以 `configs/streetscape_tiny_static.json` 运行一个有限基线：
   `envs/python311/bin/python3 scripts/run_episode.py --config configs/streetscape_tiny_static.json --method baseline --seed 30 --pedestrians 0 --record --output runs/streetscape_static_probe_20261102`
   首先解决模型、观察维度、相机朝向、真实街景画面和实际移动，不能以“导入成功”代替 rollout 成功。
3. 输出并实际查看第一帧、途中帧和 MP4。验收图像能清晰辨认道路、人行道、机器人及场景物体，验证每步相机图像来自该次 env.step。相机使用第三人称跟随和后续第一视角；不以顶视示意图作为主视频。
4. 基线在 tiny 的迁移效果须如实测量。通过静态基线后才启用 `configs/streetscape_tiny_dynamic.json` 和既有行人资产；先核对实际行人数、轨迹和碰撞标志，再测试限速/预测模块。开发集先处理已知的后优化限速风险，不能照搬二维改善结论。
5. 开发/测试分离，冻结新协议，对相同场景/目标/种子做小规模配对；保存真实 RGB、动作、轨迹、失败和所有指标。若策略效果有限，报告迁移失败与可行性，不手填成功。
6. 使用新的三维实测结果重写 3–5 页 proposal；二维数据仅作有明确标签的辅助证据。GenAI 部分不制作、不拼接、不在正文声称已完成。

目前未生成任何真正的三维街景 rollout；完成条件尚未达到。中央记录：`storage_management/ucmp_week3_streetscape_revision_20261102-011210/`。

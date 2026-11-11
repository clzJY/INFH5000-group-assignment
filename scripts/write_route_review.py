#!/usr/bin/env python3
"""Chinese project review generated from the accepted test tables."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    evidence=json.loads((ROOT/'outputs/route_refinement/test/summary.json').read_text())
    rows={r['method']:r for r in evidence['summary'] if r['density']=='all'}
    route=rows['route'];full=rows['route_intent']
    if full['contact_free_goals']>route['contact_free_goals'] and full['pedestrian_contacts']<=route['pedestrian_contacts']:
        recommendation='完整模块在本轮测试得到更多无接触到达，可保留为完整演示配置；但近距离暴露和耗时上升，路线模块本身也是必须保留的对照，不能宣称完整模块普遍更安全。'
    else:
        recommendation='建议把路线一致性模块作为目前的主要改进；新风险模块保留为可选研究分支。现有证据不足以把额外风险预测称为全面改善。'
    text='''# 重新审查与改进记录：2026-11-02

此次改进保留官方 MetaUrban 原生三维街景、街道物体、动态行人和 Bullet 物理。没有训练网络、启动星流或下载新资产；GenAI 作业部分继续按要求留待后续。

## 原来的问题是什么

1. **到达标准过粗。** 旧版 native arrival 使用路线投影完成度 >95% 或短路线分支。在旧实验的 23 次原生成功中，只有 6 次结束点距目标 <=2 m，而这 6 次全部来自起终点重合的退化任务。其余成功都未满足这一更严格的定义；非退化基线成功结束点距目标约 5–17 m。旧协议本身没有采用 2 m 标准，因此保留原始统计并明确区分口径。
2. **直线预测忽略路线和转向。** 旧预测在加速意图下从静止假设前进，可能长期等待。旧 seed108 的两个人数条件等待约 55 秒；当前相距数米也可能因预测路径而停住。
3. **停车不必然安全。** 本轮开发案例中，机器人停住后行人仍沿预规划路径前进并碰到机器人。风险判定需要比较不同动作产生的后果。
4. **半径和碰撞体不一致。** 行人声明半径为 0.35 m，但原生碰撞盒平面尺寸为 1×1 m；粗代理不是实际碰撞体距离。分离轴间隙也只是分离矩形距离的下界，会在斜向接近时低估间距。
5. **部分失败与风险层无关。** PPO 输出负油门时，统一禁止倒车的接口只会制动，一些场景因此停滞。独立倒车兼容探针也未解决所选失败，记录保留。单纯给旧风险层增加阈值，不能修复全部到达问题。

## 实施的改进

- 新实现隔离在 `src/streetscape_route/`，没有修改旧冻结代码或原始 60 次实验。
- 加入小型路线一致性模块：在路线偏离、转向分歧或剩余路线上的不合适制动时，修正 steering/throttle，并采用速度和曲率限制。它读取完整参考路线，属于额外的特权信息；不能把所有收益归因于风险几何。
- 新风险层沿前方路线预测不同速度，使用原生碰撞盒的二维足迹；分离时计算精确平面欧氏间距，重叠时记录分离轴穿透量。
- 明确比较继续、减速和停车；如果没有满足 buffer 的候选，显式记录无可行候选状态，必要时使用预测重叠较小的动作。这不是安全保证。
- 统一要求 `native arrival AND 目标点距离 <=2m`，早到的原生标记单独保留；不得仅因原生标记而结束任务。
- 生成任务开始前检查路线和起终点距离均 >=5m。异常任务不补抽；超过20m/s的数值异常也保留在主结果中并标记。

## 冻结后的新测试

开发集为900–904，新测试为此前未使用的200–209，每个种子5/15人，四方法共80次。冻结后未按测试结果改参数。下表到达要求在目标2m范围，行人接触按episode计数。

| 方法 | 有效任务 | 严格到达 | 原生成功标记 | 行人接触 | 无任何接触的严格到达 |
|---|---:|---:|---:|---:|---:|
'''
    for m,name in [('baseline','PPO'),('predictive','旧CV让行'),('route','路线一致性'),('route_intent','路线+新风险层')]:
        r=rows[m];text+=f"| {name} | {r['valid']} | {r['strict_goals']} | {r['native_goals']} | {r['pedestrian_contacts']} | {r['contact_free_goals']} |\n"
    text+='\n'+recommendation+'\n\n'
    pair=next(x for x in evidence['paired'] if x['control']=='route' and x['method']=='route_intent')
    text+=f"新风险层的近距离代理暴露为 {100*full['mean_near_fraction']:.2f}%，路线模块单独使用为 {100*route['mean_near_fraction']:.2f}%；在相同的{pair['jointly_successful_n']}个成功条件上平均增加{pair['mean_joint_delay_s']:.2f}s。完整模块路线修正门在约{100*full['mean_route_correction_fraction']:.1f}%的步数中激活。因此，到达收益主要需要结合路线/动作修正来解释，额外风险层的接触、暴露与效率存在权衡。\n\n"
    text+='''到达、接触和无接触到达分开判断；原生成功不能替代具体目标点距离。全部失败保留，`outputs/route_refinement/figures/all_conditions.png` 展示所有匹配条件。样本共享场景种子，不把20个条件当成20个独立城市布局，也不据此声称真实世界安全。

## 实际三维演示与文件

- [新对比视频](../outputs/route_refinement/videos/development_route_comparison.mp4)：开发集902、高人数，相同初始场景；终止后的画面明确标注保持。
- [到达、停车、保存街景](../outputs/route_refinement/videos/inspection_mission.mp4)：40.9s进入目标2m范围，停车阶段最后一秒最高实测速率0.074m/s；相机转90度，保存真实RGB。导航与无画面运行位置、动作最大差均为0。
- [保存的街景](../outputs/route_refinement/videos/inspection_view.png)。
- [新测试失败案例](../outputs/route_refinement/videos/first_test_failure.mp4)：预先选定最低测试种子200、低人数，保留失败，不并入成功展示。
- [逐次数据](../outputs/route_refinement/test/episodes.csv)、[汇总](../outputs/route_refinement/test/summary.csv)、[匹配差异](../outputs/route_refinement/test/paired.csv)。
- [新版Proposal PDF](../report/Week3_Streetscape_Research_Proposal_v2.pdf)、[Word](../report/Week3_Streetscape_Research_Proposal_v2.docx)。旧版文件仍保留。
- [完整复现说明](route_refinement_reproduction.txt)。
- [中央记录](../../../../storage_management/ucmp_week3_refinement_20261102-094512/README.md)：冻结、逐步重算、视频一致性、缓存清理清单和交付hash。

## 空间管理

清理仅包括可再生成的Python/pytest缓存，首次按文件大小累计296,089,621字节。没有删除原始资产、环境、源代码、冻结实验、失败轨迹或旧发布包。新视频的单片入口使用硬链接，避免再复制一份视频数据。清理清单和执行日志集中记录，后续如有额外临时缓存清理另列新清单。
'''
    (ROOT/'docs/refinement_review_20261102.md').write_text(text)
    top=f'''# Week 3：新版严格到达与路线/风险改进

最新交付见 [重新审查、结果与文件入口](docs/refinement_review_20261102.md)。新版 Proposal：[PDF](report/Week3_Streetscape_Research_Proposal_v2.pdf) / [Word](report/Week3_Streetscape_Research_Proposal_v2.docx)。

新增80次冻结测试、40次最终开发运行；目标标准统一为进入目标2m范围并满足原生到达标记。PPO严格到达 {rows['baseline']['strict_goals']}/{rows['baseline']['valid']}，路线一致性 {route['strict_goals']}/{route['valid']}，路线+新风险层 {full['strict_goals']}/{full['valid']}。{recommendation}

先看 [真实三维对比视频](outputs/route_refinement/videos/development_route_comparison.mp4) 和 [导航—停车—记录街景](outputs/route_refinement/videos/inspection_mission.mp4)。GenAI部分按用户要求待后续处理。

以下是上一版实验的历史说明，使用较宽松的原生到达标准；原始代码、数据与发布包保留，不能与新版数字直接混合。

---

'''
    readme=ROOT/'README.md';old=readme.read_text()
    assert not old.startswith('# Week 3：新版严格到达'), 'Do not append duplicate release headers'
    readme.write_text(top+old)


if __name__=='__main__':main()

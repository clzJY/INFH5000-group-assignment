#!/usr/bin/env python3
"""Readable Chinese account generated from accepted, unpooled evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'outputs/classical';OP=ROOT.parents[2]/'storage_management/ucmp_week3_classical_baselines_20261102-104447'
NAMES={'pp':'PP + 公共静态保护','rpp':'RPP-inspired','distance':'当前距离让行','forecast_static':'零速度预测消融','forecast':'路线 + 速度预测','dwa':'DWA-style'}

def main():
 e=json.loads((B/'test/summary.json').read_text());c=json.loads((B/'encounter_test/summary.json').read_text());r={x['method']:x for x in e['summary'] if x['density']=='all'};f=r['forecast'];p=r['rpp'];z=r['forecast_static'];w=r['dwa'];n=f['valid']
 intervals=json.loads((B/'test/paired_cluster_intervals.json').read_text())['contrasts']
 lines=['# 新一轮经典基线对照与小型预测模块研究','',
 '本轮已完成本地原生三维实验。没有下载、训练模型或启动星流，**没有清理或删除文件**。旧版 proposal 原件和逐字节副本全部保留，新增 v3。GenAI 声明与截图继续按你的要求留待后续。','',
 '## 先看这些文件','',
 '- [v3 Proposal PDF](../report/Week3_Streetscape_Research_Proposal_v3.pdf) / [可编辑 Word](../report/Week3_Streetscape_Research_Proposal_v3.docx)：五页，含两幅实际结果/街景图和六篇参考文献。',
 '- [真实三维横穿对比](../outputs/classical/videos/classical_crossing_comparison.mp4)：RPP-inspired、预测模块、DWA-style，同一开发场景、同一行人运动；不是总体成绩的替代。',
 '- [到达—停车—保存街景](../outputs/classical/videos/inspection_mission.mp4) / [实际保存图片](../outputs/classical/videos/inspection_view.png)。',
 '- [固定障碍边界案例](../outputs/classical/videos/stationary_limitation.mp4)：保留无法绕开的失败。',
 '- [论文与方法的通俗解释](classical_literature_and_design_20261102.md) / [完整复现流程](classical_reproduction_20261102.txt)。','',
 '## 这次修正了比较方式','',
 '此前 PPO 到达率偏低，涉及路线信息、动作接口、训练任务与转移条件，不能代表成熟经典控制。新一轮取消神经策略推理，六种方法共用完整路线、当前状态/行人速度、原生平面碰撞盒、有限制动和静态物体保护。RPP-inspired 与 DWA-style 是适配版本，没有声称完整复现原论文或 Nav2。',
 '预测模块只做一个小问题：沿现有路线预测不同速度的后果。零速度消融保留同样的候选/几何/代码，只把行人速度置零，直接检验速度信息的作用。DWA-style 额外搜索转角，帮助了解速度选择的边界。','',
 '## 冻结后的随机街景结果','',
 f'开发48次，测试120次（6方法 × 5/15人 × 10个新seed300–309）。每方法请求20个匹配条件，有效{n}个，无效{20-n}个；无效任务按预先规则保留，不补抽。严格到达要求原生标记且距终点≤2m。','',
 '| 方法 | 严格到达 | 行人接触 | 无任何接触到达 | 平均等待 s | 平均盒距离<1m时间比例 |',
 '|---|---:|---:|---:|---:|---:|']
 for m,name in NAMES.items():
  x=r[m];lines.append(f"| {name} | {x['strict_goals']}/{n} | {x['pedestrian_contacts']}/{n} | {x['contact_free_goals']}/{n} | {x['mean_wait_s']:.2f} | {100*x['mean_box_near_fraction']:.2f}% |")
 lines+=['','![所有匹配条件](../outputs/classical/figures/all_conditions.png)','',
 '接触数按 episode 计；无任何接触到达还排除静态物体、建筑、人行道等接触。近距离比例使用原生平面盒间距，和 v2 的圆形代理不是同一指标；它也不等于舒适感。','',
 '### 预测的实际增量','']
 for control in ['rpp','distance','forecast_static','dwa']:
  x=next(a for a in e['paired'] if a['control']==control and a['method']=='forecast');delay='无共同成功条件' if x['mean_joint_delay_s'] is None else f"在{x['jointly_successful_n']}个共同成功条件上耗时差{x['mean_joint_delay_s']:+.2f}s"
  lines.append(f"- 相对{NAMES[control]}：挽回{x['rescued']}个到达、退化{x['regressed']}个；无接触到达净变化{x['contact_free_goal_delta']:+d}个；{delay}。")
 lines+=['',f"速度预测与零速度消融的行人接触分别为{f['pedestrian_contacts']}和{z['pedestrian_contacts']}；无接触到达分别为{f['contact_free_goals']}和{z['contact_free_goals']}。这是对新增速度信息最直接的对照，不能把全部路线跟踪收益算给预测。",'']
 delta=f['contact_free_goals']-p['contact_free_goals']
 if delta>0:lines.append(f'本轮相对 RPP-inspired 多了{delta}次无接触到达，构成一个小幅、可复查的改善；样本很小，也仍需同时看失败、等待和近距离暴露。')
 elif delta==0:lines.append('本轮预测模块与 RPP-inspired 的无接触到达数量相同，未得到这一主要指标的提升。研究价值在于明确比较了增量与失败边界；不应为了作业把结果写成全面胜出。')
 else:lines.append(f'本轮预测模块相对 RPP-inspired 少了{-delta}次无接触到达，因此不支持在这一主要指标上更优。应据实保留，其他效率或接触差异只能作为有限观察。')
 lines.append(f"作为更简单的对照，PP+公共静态保护也得到{r['pp']['strict_goals']}次到达、{r['pp']['contact_free_goals']}次无接触到达，平均等待{r['pp']['mean_wait_s']:.2f}s、近距离暴露{100*r['pp']['mean_box_near_fraction']:.2f}%；预测版本分别为{f['mean_wait_s']:.2f}s和{100*f['mean_box_near_fraction']:.2f}%。本轮没有证明新增预测复杂度适合作为默认方案。")
 for item in intervals:
  if item['control']=='rpp' and item['metric']=='contact_free_goal':
   lo,hi=item['percentile95'];lines.append(f"按10个场景seed整组重采样、保留两个人数条件，预测减RPP的无接触到达差为{100*item['mean_difference']:+.1f}个百分点，描述性95%区间[{100*lo:.1f}, {100*hi:.1f}]个百分点。这些配对结果逐项相同，因此自助区间退化为零；它不证明总体差异为零，也不是等效性检验。小样本不支持罕见风险承诺。")
 lines+=['','## 单行人诊断：单独报告','',
 '开发20次，另用seed320–321完成40次新测试。横穿、远离、迎面和静止分别为2个条件。行人按规定轨迹放置，机器人完全使用原生物理；控制器不读取未来脚本。这是用于解释机制的受控实验，不能与随机5/15人街景合并。','',
 '| 相遇类型 | RPP无接触到达/2 | 距离/2 | 零速度/2 | 预测/2 | DWA/2 |','|---|---:|---:|---:|---:|---:|']
 for kind,label in [('crossing','横穿'),('receding','远离'),('approaching','迎面接近'),('stationary','固定障碍')]:
  vals=[next(x['contact_free_goals'] for x in c['summary'] if x['density']==kind and x['method']==m) for m in ['rpp','distance','forecast_static','forecast','dwa']];lines.append('| '+label+' | '+' | '.join(map(str,vals))+' |')
 lines+=['',
 '- 横穿时，预测平均等待0s，RPP-inspired约1s；但预测的<1m暴露为2.42%，RPP为0%。这是效率与近距离暴露的权衡。',
 '- 远离时，所有方法均无接触完成；不能声称本轮已经证明预测在远离场景优于所有基线。',
 '- 迎面时，四个只调速的版本都在两个条件发生接触；DWA-style得到一次无接触到达，另一次未到达。这说明横向选择可能重要，仍不构成统一优势。',
 '- 静止时，所有方法均未完成。沿既定路线快慢选择不能替代真正绕行/重规划。',
 '', '## 验证、保留和局限','',
 '47项测试通过；开发数据29,466步、受控新测试19,050步及随机新测试的全部决策已独立重放/重算。冻结源文件22份；同一条件初始路线、状态和几何一致。真实RGB重复与无画面运行位置/动作/行人差异均为0。停车演示末一秒最高实测速率约0.065m/s。',
 '使用理想状态和完整路线；预测忽略未来转向速率限制和详细轮胎瞬态，碰撞盒也只是采样平面近似。静态保护不覆盖完整道路/路沿网格。短时几何可行不等于真实安全，行人脚本或预规划也不是自然人的互惠反应。每个人数条件共享场景seed，不能当作20个独立城市布局。','',
 '## 作业对应与下一步','', '五个沿给定路线跟踪的版本共同在seed305/306、5/15人时超时，共4个条件。末步移动候选均未通过静态足迹buffer，停车候选通过；这表明检查造成长期停顿，并不证明物理路线无法通行。DWA-style却完成了这4个条件，其中3个无接触，但又在预测版本能完成的另6个条件失败。因此，有条件地增加横向选择，比把全程控制都换成DWA更值得进一步检验。','',
 'v3按Option1组织：具体城市研究问题、公共空间与社会导航评估视角、数据/变量/空间单位、公平方法/消融、预实验结果、120次可行后续计划及不确定性/伦理讨论。预实验可以保留负结果，并不要求SOTA。主文五页、六篇文献；GenAI附录仍待你后续完成。',
 '后续proposal聚焦一个尚未实现的小绕行触发器：静态足迹检查导致停车超过3秒时，尝试左右不超过1.5m的局部航点，仍须通过足迹buffer与可行走区域检查，否则继续等待。用10个新seed × 2布局家族 × 2人数 × 3方法（RPP、预测、预测+绕行）共120次检验。先开发与冻结，再跑新seed；不把未实施模块写成已有成绩。','',
 '- [正式逐episode CSV](../outputs/classical/test/episodes.csv) / [汇总](../outputs/classical/test/summary.csv) / [匹配差异](../outputs/classical/test/paired.csv)。',
 '- [全部失败/接触索引](../outputs/classical/failure_index.json)。',
 '- [版本索引与旧版入口](../report/VERSIONS.md)。',
 '- [中央执行、验收和发布记录](../../../../storage_management/ucmp_week3_classical_baselines_20261102-104447/README.md)。',
 '', '本轮不执行清理。日志去重仅改变新运行的写入方式，旧日志、旧proposal和旧发布包全部保持原样。','']
 (ROOT/'docs/classical_review_20261102.md').write_text('\n'.join(lines))
 # Prepend the current entry, retaining the complete previous README text.
 readme=ROOT/'README.md';old=readme.read_text();marker='# Week 3：共享输入的经典基线研究（v3）'
 if not old.startswith(marker):readme.write_text(marker+'\n\n最新交付：[v3 PDF](report/Week3_Streetscape_Research_Proposal_v3.pdf) / [Word](report/Week3_Streetscape_Research_Proposal_v3.docx)，以及[新结果与通俗解释](docs/classical_review_20261102.md)。\n\n完成120次冻结随机街景测试、40次单行人测试、68次开发运行。使用共享路线/状态的PP、RPP-inspired、距离、零速度消融、速度预测和DWA-style；不再以PPO为主要比较。真实三维[横穿对比](outputs/classical/videos/classical_crossing_comparison.mp4)与[导航停车街景](outputs/classical/videos/inspection_mission.mp4)均经轨迹一致性验证。\n\n旧版proposal和全部历史数据保留，本轮没有清理。GenAI部分继续待后续。下方为完整历史说明，各轮统计口径不同，不直接合并。\n\n---\n\n'+old)
 versions=ROOT/'report/VERSIONS.md';text=versions.read_text()
 if 'Week3_Streetscape_Research_Proposal_v3.pdf' not in text:text+='\n- [v3 PDF](Week3_Streetscape_Research_Proposal_v3.pdf) / [Word](Week3_Streetscape_Research_Proposal_v3.docx): shared-input classical baselines, 120 random-street +40 separately reported controlled fresh runs; no neural inference.\n'
 versions.write_text(text)
 print('REVIEW_AND_INDEX_WRITTEN')

if __name__=='__main__':main()

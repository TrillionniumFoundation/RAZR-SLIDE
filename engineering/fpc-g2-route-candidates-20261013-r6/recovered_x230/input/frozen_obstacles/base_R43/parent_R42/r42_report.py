import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
load=lambda name:json.loads((ROOT/'verification'/name).read_text())
def run():
 motion=load('R42_motion_budget.json'); occ=load('R42_OCC_two_flexes.json');bound=load('R42_reverse_U_bound.json');att=load('R42_attest.json');inside=load('R42_interior_points.json')
 assert len(occ['ghost_poses'])==9 and len(inside['rows'])==18 and motion['math_cases']==242 and att['fresh_total_tests']==846
 st=[]
 for p in occ['ghost_poses']:
  c=p['collisions_with_original_protected_bodies_mm3'];
  st.append({'stage':p['stage'],'s_mm':p['s_mm'],'q_mm':p['q_mm'],
        'A_core_mm3':round(sum(x['A_R38_PROTECTED'] for x in c.values()),6),
        'B_core_mm3':round(sum(x['B_R38_PROTECTED'] for x in c.values()),6),
        'OLED_proxy_mm3':round(sum(x['OLED_NO_VENDOR'] for x in c.values()),6),
        'display_FPC_mm3':round(sum(x['DISPLAY_FPC_NOT_CROSS_CHAMBER'] for x in c.values()),6),
        'two_ribbon_self_overlap_mm3':p['two_ribbons_nominal_intersection_mm3']})
 summary={'revision':'R42: mathematical moving mid-junction and two FPCs; engineering rejection',
     'products':'A/B equal finished outer dimensions TARGET, single 7-inch OLED, B up 79.75 then Z dock 8.2, A priority battery',
     'parent_R41_original_sha256':att['frozen_parent_R41_full_zip_sha256'],
     'math_positions':121,'math_FPC_case_count':242,
     'maximum_analytic_length_error_mm':motion['maximum_abs_solved_length_error_mm'],
     'min_calculated_radius_mm':motion['minimum_bend_centerline_radius_mm'],
     'two_FPC_lengths_mm':motion['section_lengths_mm'],
     'total_research_FPC_length_mm':motion['total_flex_length_mm'],
     'test_scenarios_Occ_poses':len(st),'occ_poses_with_named_protected_collision':occ['poses_with_protected_obstruction'],
     'occ_poses_with_A_protected_overlap':sum(x['A_core_mm3']>1e-6 for x in st),
     'occ_poses_with_B_protected_overlap':sum(x['B_core_mm3']>1e-6 for x in st),
     'occ_poses_with_OLED_proxy_overlap':sum(x['OLED_proxy_mm3']>1e-6 for x in st),
     'two_FPC_overlap_poses':sum(x['two_ribbon_self_overlap_mm3']>1e-6 for x in st),
     'max_two_FPC_overlap_mm3':max(x['two_ribbon_self_overlap_mm3'] for x in st),
     'max_OLED_proxy_overlap_mm3':max(x['OLED_proxy_mm3'] for x in st),
     'A_carriage_in_core_each_pose':all(p['collisions_with_original_protected_bodies_mm3']['GHOST_MID_CARRIAGE_WITHOUT_MOUNTS']['A_R38_PROTECTED']>0 for p in occ['ghost_poses']),
     'each_FPC_has_core_interior_hits_away_from_3mm_terminal':all(x['interior_point_hits']['A']+x['interior_point_hits']['B']>0 for x in inside['rows']),
     'opposite_single_U_stow_Y_outside_mm_minimum':bound['required_outside_Y_at_stow_mm'],
     'opposite_single_U_necessary_condition_fails':not bound['feasible_single_negative_Y_U_under_conditions'],
     'GHOST_STEPS_with_import_receipts':sum(bool(p.get('STEP_reimport')) for p in occ['ghost_poses']),
     'fresh_research_tests':att['fresh_total_tests'],
     'old_mechanical_36_out_of_64_hazards_unresolved':True,
     'real_OEM_A_B_protected_volume_permissions_missing':True,
     'actual_FPC_dynamic_life_silicon_copper_stack_missing':True,
     'moving_junction_driving_hardware_unbuilt':True,
     'power_USB_BM28_wiring_not_proven':True,
     'manufacturing_go':False,'candidate_go':False,'negative_examples':'These tests pass by correctly recognizing colliding/unmanufacturable geometries'}
 (ROOT/'R42_results_20261013.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
 lines=['# RAZR SLIDE R42｜双段 FPC + 半速中间载体的 OCC 对抗审计','',
 '**最终结论：研究级数学运动守恒成立，但实际 OCC 空间检查失败；`candidate_go=false`、`manufacturing_go=false`。**','',
 '## 1. 冻结父档与产品方向','',
 '- 冻结 R41 完整父包 SHA256：`'+att['frozen_parent_R41_full_zip_sha256']+'`；57 个成员、CRC 校验通过，R40/R39/R38 历史嵌套只读。','- A/B 两块**目标同外形**完整功能舱，B 向上滑 79.75mm 后 Z 就位 8.2mm；仅一块约 7 英寸柔性主屏，无独立外屏；A 优先大电池。成品等尺寸、电芯 4700mAh、OEM 机芯/屏幕 3D 均未获得制造许可。','',
 '## 2. 与 R41 单回环不同的真实建模方案','',
 '- 两条**互相独立**的研究 FPC，均以 R16.5 的 XY 半圆 U 和平滑 Z 过渡解算。不是一整片 FPC：A → C、C → B 之间必须有移动的中继电路/端接。','- A 固定 `[33,70,6.05]mm`，B 收纳 `[33,15,-3.40]mm`、展开 `[33,94.75,4.80]mm`；中间未建成的 C 从 `[0,15,1.325]mm` 到 `[0,54.875,5.425]mm`，需要半速 Y=39.875mm、Z=4.10mm 真实机械传动。','- 假设的两条中心线长度分别 113mm 与 99mm，总长度 212mm；宽 1.2mm、厚 0.15mm。所有固定长度和曲率均是研究假设，未经 FPC 供应商动态许可。','- 121 个真实顺序运动工位（先 101 个 Y，再 20 个 Z）× 两条 FPC = 242 次解析求解；最大长度误差 `%.3gmm`，最小解析半径 `%.6fmm`，解析中心线名义外包络无 X/Y/Z 越界。**数学守恒不等于铜箔应力或连续实体无碰撞。**'%(motion['maximum_abs_solved_length_error_mm'],motion['minimum_bend_centerline_radius_mm']),'',
 '## 3. 实际 OCC 带状扫掠否决','',
 'A/B/R38 保护 BRep、旧 OLED/显示 FPC 研究体保持原件，**没有切除任何受保护机芯体积**。每段曲线单独扫掠 1.2×0.15mm 实体，加入 4×3×0.6mm **未装配**中继载体代理，对九个运动工位按完整实体求交。','',
 '| 工位 | A 保护实体重叠 mm³ | B 保护实体重叠 mm³ | OLED 研究体重叠 mm³ | 两段线路自重叠 mm³ |','|---|---:|---:|---:|---:|']
 for row in st:lines.append('| %s (s=%.3f, q=%.3f) | %.4f | %.4f | %.4f | %.4f |'%(row['stage'],row['s_mm'],row['q_mm'],row['A_core_mm3'],row['B_core_mm3'],row['OLED_proxy_mm3'],row['two_ribbon_self_overlap_mm3']))
 lines.extend(['',
 '- **9/9 个姿态有与指定受保护体积重叠；两段 FPC 在 9/9 姿态互相占用体积**。其中未建成中间载体 7.2mm³ 的代理体积在这九个姿态中均与 A 研究实体重合。','- 剔除 FPC 两端各 3mm 的焊盘/端头可能接触区以后，18 条 FPC-姿态内部中心线样本仍全部进入 A/B 研究保护实体；不应把碰撞归咎于端头局部合理接触。中心线分类只起佐证作用，OCC 体积求交是九姿态的主要证据。','- 3 份 STEP（收纳、未坐实终点、完全坐实）均可重导入有效实体，**全部为故意保存的失败 GHOST，不是功能样机**。','- 九个工位是离散而非连续扫掠；尽管当前每个受检姿态均已失败，不能据此推导对所有可能动态布局的全局无解结论。','',
 '## 4. 反向第二个 U 形回环的必要空间界','',
 '- 只针对 C→B 的单个 R16.5、180°、朝负 Y 方向的 U；中间载体 Y 随 B 半速移动，收纳锚点 Y=15，收纳实体要求 Y≥0。此限定**不覆盖其他多回环、三维/折线/储线盒拓扑**。',
 '- 展开端点相距 39.875mm，必须有 FPC 长度至少 `%.6fmm`；要使收纳 U 完整留在 Y≥0，又最多允许 `%.6fmm`，两条件矛盾。'%(bound['minimum_FPC_length_for_final_separation_mm'],bound['maximum_FPC_length_that_fits_stow_Y_min_mm']),
 '- 即便取最短可展开线路，收纳回环仍至少有 `%.6fmm` 落在 Y=0 以外；该简单反向 U 被尺寸边界否决。'%bound['required_outside_Y_at_stow_mm'],'',
 '## 5. 回归、证据边界与制造硬门槛','',
 '- 实际重新运行 R21–R38 继承 697 项、R39 31 项、R40 38 项、R41 42 项，合计 808 项；R42 新增 38 项；**总计 846/846 个研究级断言通过**，每组具有本轮实际退出码/日志。很多断言通过是因为准确捕获危险，绝非全机安全合格。',
 '- 最基本的 F/M/P/S/U/D 仍缺：供应商实际动态 FPC、可授权变更的 OEM 机芯保护模型、半速载体真实驱动、机械捕获与失效常闭（旧 36/64 危险逃逸仍未解决）、双电池保护及三种 PCB 单点旁路、USB SI、Hirose BM28 实装及 OLED 完整模组资料。',
 '- 禁止在未经批准的 BRep 上切槽后把结果宣称为制造可行；不允许以 R15/R16.5 作为 300,000 次寿命证书，也不允许将两条独立 FPC 的抽象连接点解释为已经接通的电路。','',
 '## 6. 下一道值得投入的门槛（R43）','',
 '**先取得 OEM 明确的实际可改体积、真实 7 英寸 OLED 完整叠层、可采购动态 FPC 材料与端接图纸**；在此基础上定量重新分配侧/屏后 cassette、双独立服务环和中继载体安装位置。若没有这些资料，继续只平移虚构 FPC 的研发边际收益很低。每个新拓扑均须先按实际 A/B 外壳/导轨/电池约束和安装顺序作实体无干涉检查，然后进行受载及 300k 次实物试验。',
 '', '**R42 维持 `candidate_go=false`、`manufacturing_go=false`，严格禁止制造放行。**'])
 (ROOT/'R42_hardgate_audit_20261013.md').write_text('\n'.join(lines)+'\n')
 return summary
if __name__=='__main__':run()

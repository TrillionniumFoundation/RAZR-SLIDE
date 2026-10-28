"""Map all 228 original requirements into field delivery tasks without inventing observations."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

def ident(path):
    b = Path(path).read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def write(path, data):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--original-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    original = a.original_root / 'original-contract-and-template'
    contract_path = original / 'R3_SAME_SPECIMEN_INTAKE_CONTRACT.json'
    contract = json.loads(contract_path.read_text())
    if ident(contract_path)['sha256'] != '876ca9a54ba94fe6be7695ab641435cdcd69709ff21bf093898f30a09fd36a5a':
        raise ValueError('frozen original contract changed')
    a.output.mkdir(parents=True, exist_ok=True)
    for source in (contract_path, original / 'R3_EMPTY_INTAKE_PACKET.json',
                   a.original_root / 'source-and-results' / 'verify_intake_r3_v2.py'):
        target = a.output / source.name
        if target.exists():
            raise FileExistsError(target)
        shutil.copyfile(source, target)
        if ident(source) != ident(target):
            raise ValueError('original byte copy mismatch')
    groups = {
        'identity': {'owner': '现场样件保管／计量／电气', 'stage': 'D0',
            'delivery': ['同一样件的未编辑全机／标签照片及采集日志', '逐项身份值和原文件内定位；公开型号页面不能充当该样件身份'],
            'acceptance': ['照片或日志必须绑定同一 specimen_id', '10 项逐项有值；看不到或无法读取时保留 null 和缺失原因']},
        'part': {'owner': '现场计量／机械／显示／电气', 'stage': 'D1',
            'delivery': ['原件整体与标签原照片、实际 PN/revision、零件唯一标识',
                         '外包／禁入尺寸、坐标基准、装拆／尾出／配合方向和 pin 1 原始观察',
                         '原始读数、单位、不确定度类型、仪器和有效校准记录；原机功能基线'],
            'acceptance': ['每项绑定 specimen_id 与声明 part_id', '集成部件可由同一真实 part_id 承担多个角色，但不能据此省略角色事实',
                           '不能由比例图片推定真实尺寸或不确定度']},
        'interface': {'owner': 'OEM 互连／电气／计量', 'stage': 'D2',
            'delivery': ['同一样件逐端子表，列出两端 PN/revision/pin 1/引脚号',
                         '信号／方向／回流与屏蔽、原端子来源定位、原机功能协议与测得基线',
                         '有来源的电气限制、原始记录和不确定度'],
            'acceptance': ['12 个接口分别列全部端子，不能只交接口名称', '公开系列 BOM 不等于该样件的端子映射',
                           '方向、回流、两端配对和原文件定位必须同时可追溯']},
        'supplier': {'owner': '显示／柔性互连／连接器／材料工艺', 'stage': 'D3',
            'delivery': ['选定实际 PN/revision 的原厂或受控制造图／工艺文件',
                         '本要求的具体参数、条件、版本与页／图／表定位',
                         '适用零件、lot、原件和同一样件观察之间的对应'],
            'acceptance': ['21 项逐项对应原描述；不以“收到一份 PDF”自动填满整个角色',
                           '叠层、弯曲方向、动态半径／应变／力／温度／循环限制不得用通用经验值补齐']}}
    tasks = []
    for r in contract['requirements']:
        g = groups[r['category']]
        tasks.append({'requirement': r, 'state': 'UNACQUIRED', 'observed_value': None,
            'evidence_ids': [], 'source_locator': None, 'source_revision': None,
            'owner_role': g['owner'], 'collection_stage': g['stage'],
            'required_delivery': g['delivery'], 'acceptance': g['acceptance'],
            'measurement_record_fields_when_applicable': contract['measurement_record_requirements']})
    plan = {'schema': 'razr-r5-field-collection-plan-v1', 'is_template': True,
        'original_contract_identity': ident(contract_path),
        'original_requirement_count': len(contract['requirements']),
        'original_requirement_ids_and_descriptions_preserved': True,
        'counts': contract['counts'], 'requirements': tasks,
        'specimen_id': None, 'candidate_id': None, 'functional_commit': None,
        'geometry_revision': None, 'assembly_revision': None,
        'gate_order': contract['gate_admission'],
        'all_17_motion_phases': contract['original_G3_G4_G5_contract']['plan_templates']['G3-EP5-plan.template.json']['planned_phase_order'],
        'remaining_plan_and_threshold_contract': contract['original_G3_G4_G5_contract'],
        'current_FE_and_tolerance_contract': contract['original_FE_contract'],
        'field_collection_is_not_authorization_to_disassemble_or_run_unsourced_tests': True,
        'physical_gate_pass': {'G3': False, 'G4': False, 'G5': False},
        'original_intake_schema_and_validator_changed': False}
    write(a.output / 'R5_FIELD_COLLECTION_PLAN.json', plan)
    write(a.output / 'R5_EMPTY_EVIDENCE_INVENTORY.json', {
        'schema': 'razr-r5-evidence-receipt-inventory-v1', 'is_template': True,
        'files': [], 'row_template': {'evidence_id': None, 'path': None,
            'evidence_kind': None, 'specimen_id': None, 'acquired_at_utc': None,
            'acquirer': None, 'method': None, 'source_locator': None,
            'expected_identity': None},
        'instructions': ['files 只加入实际收到的原文件；row_template 不作为证据。',
            '原始图片／日志保持原字节；裁剪注释另存派生件。',
            '填写原 packet 内对应事实和引用；工具不会从文件名、网页或照片自动推断数值。',
            '缺测、失败、维修、换件分别记事件；同候选同样件新 assembly_revision 重建 G3→G4→G5 链。']})
    write(a.output / 'R5_ORIGINAL_INPUT_IDENTITIES.json', {
        'schema': 'razr-r5-original-intake-identity-lock-v1',
        'files': {n: ident(a.output / n) for n in ('R3_SAME_SPECIMEN_INTAKE_CONTRACT.json',
            'R3_EMPTY_INTAKE_PACKET.json', 'verify_intake_r3_v2.py')}})
    print(json.dumps({'requirements': len(tasks), 'new_original_observations': 0,
                      'originals_copied_byte_identically': 3}))

if __name__ == '__main__':
    main()

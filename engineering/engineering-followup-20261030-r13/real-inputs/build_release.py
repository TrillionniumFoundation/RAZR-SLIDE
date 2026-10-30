"""Build a metadata-only R13 OEM-input handoff; no third-party bodies are public."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'RAZR-SLIDE'
OUT = HERE / 'public'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ident(path, name=None):
    return {'path': name or str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def write(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    uk = 'https://en-gb.support.motorola.com/app/right-to-repair'
    us = 'https://en-us.support.motorola.com/app/right-to-repair'
    replacement_base = 'https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/'
    source_rows = [
        {'id': 'motorola_uk_route', 'url': uk, 'publisher': 'Motorola',
         'observed': 'Official page links ReplaceBase repair documents, and lists ReplaceBase, Spares Nordics, Mobiparts and Sifar Group as parts partners.',
         'linked_repair_documents': 'https://www.replacebase.co.uk/motorola-guide',
         'linked_parts_site': 'https://motorola.replacebase.co.uk/',
         'access': 'Readable official web page; no login used.'},
        {'id': 'motorola_us_route', 'url': us, 'publisher': 'Motorola',
         'observed': 'Official page identifies iFixit and MobileSentrix partnerships; repair documents linked to MobileSentrix.',
         'linked_manual_directory': 'https://motorola.mobilesentrix.com/motorola-repair-manual',
         'access': 'Readable official web page. Manual directory shows a JavaScript-dependent series selector; no exact full document obtained there.'},
        {'id': 'replacebase_oem_route', 'url': 'https://www.replacebase.co.uk/genuine-motorola-parts',
         'publisher': 'ReplaceBase, manufacturer-linked distributor',
         'observed': 'Public search index identifies its Motorola-authorized parts and repair-manual directory.',
         'access': 'Current direct page fetch via web returns 405; direct BOM response separately confirms Human Verification.'},
        {'id': 'spares_display', 'url': 'https://www.spares.se/product/motorola-razr-60-ultra-5g-lcd-display-original-scarab',
         'publisher': 'Spares Nordics, manufacturer-linked distributor',
         'observed': 'Scarab display listing names XT2551-6 and SKU 5D68C30085.',
         'access': 'Readable product page; no purchase or login.'},
        {'id': 'mobiparts_display', 'url': 'https://www.mobiparts.ro/spare-parts-motorola/lcd-display-module-for-motorola-razr-60-ultra-sub-inner-pantone-scarab',
         'publisher': 'MobiParts, manufacturer-linked distributor',
         'observed': 'Scarab service assembly listing supplies PN 5D68C30088 and 5D68C29813. It identifies a combined display/touch/frame service assembly.',
         'access': 'Readable product information; ordering requires sign-in, which was not attempted.'},
        {'id': 'replacebase_display', 'url': 'https://www.replacebase.co.uk/motorola-razr-60-ultra-replacement-screen-assembly-5d68c29813',
         'publisher': 'ReplaceBase, manufacturer-linked distributor',
         'observed': 'Indexed authorized screen assembly listing identifies 5D68C29813 and XT2551 family compatibility.',
         'access': 'Search-index metadata only; no direct verified part or technical drawing.'},
        {'id': 'lsmtron_official_components', 'url': 'https://www.lsmtron.com/us/en/business/components',
         'publisher': 'LS Mtron',
         'observed': 'Indexed official page advertises connector families and downloads. Current downloaded HTML is a client-rendered shell, without an identified GB35R PDF link.',
         'access': 'HTTP 200 HTML, SHA bound in receipt; no selected connector datasheet acquired.'},
    ]
    write('PRIMARY_SOURCE_INDEX.json', {
        'schema': 'r13.primary_oem_source_index.v1', 'recorded_utc': now,
        'research_method': 'Web search/open for source discovery and facts; one observed public BOM URL and one manufacturer page fetched for byte verification through inherited proxy after supported escalation.',
        'sources': source_rows,
        'third_party_marketplaces_or_trade_data_adopted_as_technical_sources': False,
        'all_listings_remain_model_literature_not_specimen_evidence': True,
    })

    documents = [
        {'id': 'EU_L2', 'url': replacement_base + 'XT2551-X_Moto_razr_60_ultra_razr_ultra_Service_and_Repair_Manual_V1.0.pdf',
         'level': 'L2', 'revision_label': 'V1.0 in indexed filename', 'revision_date': None,
         'market_scope': 'Multi-region indexed assembly list; file is under authorized EU distributor route.',
         'explicit_variants_in_visible_mainboard_list': ['XT2551-1', 'XT2551-2', 'XT2551-5', 'XT2551-6'],
         'observed_content_scope': 'Indexed assembly parts and service sections only; not a complete local document read.',
         'retrieval_state': 'URL located; host challenge observed on BOM, so no attempt to bypass for this document.'},
        {'id': 'EU_L3', 'url': replacement_base + 'XT2551-X_Moto_razr_60_ultra_razr_ultra_Level_3_Service_Manual_for_EU_V1.0.pdf',
         'level': 'L3', 'revision_label': 'V1.0 in indexed filename', 'revision_date': None,
         'market_scope': 'EU in indexed filename', 'exact_variant_scope_verified': False,
         'observed_content_scope': 'Indexed Motorola/Lenovo Level 3 board-layout content; complete document not read.',
         'retrieval_state': 'URL located; host challenge observed on BOM, so no attempt to bypass for this document.'},
        {'id': 'EU_BOM', 'url': replacement_base + 'Phone_Global_SBOM_Moto_razr_60_ultra_razr_ultra_EU_V1.9.pdf',
         'level': 'service_BOM', 'revision_label': 'V1.9 in indexed filename', 'revision_date': None,
         'market_scope': 'EU in indexed title/filename', 'exact_variant_scope_verified': False,
         'observed_content_scope': 'Indexed OEM service-BOM metadata; local response is a CAPTCHA HTML page.',
         'retrieval_state': 'HTTP 405; 2531 bytes HTML; not PDF; human verification required.'},
        {'id': 'NA_L2_prior',
         'url': 'https://www.ifixit.com/Document/IxsugLCmhuNaPpYx/XT2551-X_%28Moto_razr_60_ultra_%26_razr_ultra%29_Service_and_Repair_Manual_V1.0r.pdf',
         'level': 'L2', 'revision_label': 'V1.0r filename; revision table 1', 'revision_date': '2025-03-07',
         'market_scope': 'XT2551-X family listing', 'listed_pages': 283,
         'observed_content_scope': 'Public indexed preview only; no complete bytes.',
         'retrieval_state': 'Current web direct open redirect loop; prior R12 CDN fetch returned HTML.'},
        {'id': 'NA_L3_prior',
         'url': 'https://nl.ifixit.com/Document/6RFZBdGVwWbhvVhh/XT2551-X_Moto-razr-60-ultra-razr-ultra_Level-3-Service-Manual-for-NA_V1.0r.pdf',
         'level': 'L3', 'revision_label': 'V1.0r filename; revision table 1', 'revision_date': '2025-03-19',
         'market_scope': 'NA in title/filename', 'listed_pages': 87,
         'observed_content_scope': 'Public preview contains service connector identities; full reading explicitly requires a free account.',
         'retrieval_state': 'Login required for complete document; no login or direct-CDN retry attempted.'},
        {'id': 'NA_BOM_prior',
         'url': 'https://de.ifixit.com/Document/ZKsjbwghQxtwgNBa/Phone_Global_SBOM_Moto-razr-60-ultra-razr-ultra_V1.9.pdf',
         'level': 'service_BOM', 'revision_label': 'V1.9', 'revision_date': '2025-03-11',
         'market_scope': 'USA/NA', 'explicit_model_scope': ['XT2551-1', 'XT2551-2'], 'listed_pages': 2,
         'observed_content_scope': 'Public service-BOM preview; not a verified complete PDF.',
         'retrieval_state': 'Login required for complete document; no login or direct-CDN retry attempted.'},
    ]
    for row in documents:
        row.update(complete_pdf_bytes_obtained=False, complete_pdf_sha256=None,
                   same_specimen_applicability_proven=False,
                   historical_XT2551_3_board_revision_applicability_proven=False,
                   public_full_document_copy_included=False)
    write('OEM_SOURCE_APPLICABILITY.json', {
        'schema': 'r13.oem_document_applicability.v1', 'recorded_utc': now,
        'historical_software_model': 'XT2551-3',
        'historical_model_is_a_complete_specimen_identity': False,
        'newly_located_primary_distribution_documents': 3,
        'documents': documents,
        'new_literature_progress': 'Motorola UK -> ReplaceBase official repair-document route and three indexed EU/family service-document URLs located; their completeness and XT2551-3 applicability remain unverified.',
        'new_full_PDFs_acquired': 0,
        'absence_of_XT2551_3_in_complete_global_OEM_inventory_proved': False,
    })

    connectors = [
        {'reference': 'J6300', 'Motorola_service_PN': 'SCA8C09270', 'visible_model_text': 'GB35R-10S-H08', 'pins': 10, 'pitch_mm': 0.35},
        {'reference': 'J3150', 'Motorola_service_PN': 'SCA8C44152', 'pins': 40, 'pitch_mm': 0.35, 'listed_height_mm': 0.8, 'listed_gender': 'receptacle'},
        {'reference': 'J550', 'Motorola_service_PN': 'SCA8C71314', 'pins': 6, 'pitch_mm': 0.35, 'listed_role': 'battery connector'},
        {'references': ['J3100', 'J3200'], 'Motorola_service_PN': 'SCA8D57591', 'pins': 24, 'pitch_mm': 0.35, 'listed_height_mm': 0.6, 'listed_gender': 'receptacle'},
    ]
    write('PART_IDENTITY_LEADS.json', {
        'schema': 'r13.public_part_identity_leads.v1', 'recorded_utc': now,
        'scope': 'Limited manufacturer/distributor identifiers for later label comparison; no component selection or substitution.',
        'display_service_assembly_leads': [
            {'source_id': 'spares_display', 'listed_SKU': '5D68C30085', 'explicit_variant': 'XT2551-6', 'colour': 'Scarab'},
            {'source_id': 'mobiparts_display', 'listed_PNs': ['5D68C30088', '5D68C29813'], 'explicit_variant': None, 'model_family': 'Razr 60 Ultra', 'colour': 'Scarab'},
            {'source_id': 'replacebase_display', 'listed_PN': '5D68C29813', 'explicit_variant': None, 'model_family': 'XT2551'},
        ],
        'different_SKUs_equivalent_or_interchangeable': None,
        'same_specimen_selected_display_PN_and_revision': None,
        'OLED_cell_COFinternal_design_inferred_from_service_assembly': False,
        'connector_preview_source_document': 'NA_L3_prior', 'connector_preview_leads': connectors,
        'mating_plug_PN_or_revision_bound': False,
        'actual_terminal_orientation_or_pinmap_bound': False,
        'connector_material_rating_or_process_spec_adopted': False,
        'selected_OLED_COF_FPC_stackup_bound': False,
        'dimensions_or_uncertainty_for_user_specimen_obtained': False,
        'official_LS_page_is_a_selected_GB35R_datasheet': False,
        'uncontrolled_third_party_connector_catalogues_admitted': False,
    })

    receipt_names = ['bom_default_attempt.json', 'bom_approved_attempt.json', 'lsmtron_components_attempt.json']
    for name in receipt_names:
        target = OUT / 'receipts' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(HERE / 'receipts' / name, target)
    bom = json.loads((HERE / 'receipts/bom_approved_attempt.json').read_text())
    bom_body = HERE / 'private/XT2551_EU_BOM_V1.9.pdf'
    assert sha(bom_body) == bom['sha256'] and bom_body.stat().st_size == bom['bytes']
    raw = bom_body.read_bytes()
    assert not raw.startswith(b'%PDF-') and b'Human Verification' in raw and b'CAPTCHA' in raw
    ls = json.loads((HERE / 'receipts/lsmtron_components_attempt.json').read_text())
    lsbody = HERE / 'private/lsmtron_components_response.html'
    assert sha(lsbody) == ls['sha256'] and lsbody.stat().st_size == ls['bytes']
    assert not lsbody.read_bytes().startswith(b'%PDF-')
    write('ACCESS_READBACK.json', {
        'schema': 'r13.independent_response_format_readback.v1', 'recorded_utc': now,
        'network_environment': {'cloud_environment_status_tool_available_in_registry': False,
                                'network_policy_snapshot_file_present': False,
                                'default_sandbox_request_result': 'Operation not permitted',
                                'supported_escalation_request_result': 'approved; request executed using inherited proxy and normal TLS',
                                'proxy_or_TLS_settings_changed': False},
        'EU_BOM': {'status': bom['status'], 'bytes': bom['bytes'], 'sha256': bom['sha256'],
                   'response_type': 'HTML Human Verification/CAPTCHA',
                   'pdf_header': False, 'complete_pdf_obtained': False,
                   'challenge_attempted_or_solved': False,
                   'further_automatic_downloads_at_challenged_origin': 0,
                   'raw_private_path_is_not_a_public_PDF': True},
        'LS_manufacturer_page': {'status': ls['status'], 'bytes': ls['bytes'], 'sha256': ls['sha256'],
                                'response_type': 'client-rendered HTML shell', 'complete_PDF_obtained': False,
                                'GB35R_link_found_in_current_response': False},
        'raw_response_bodies_in_public_deliverable': False,
        'private_response_filename_suffix_not_used_as_format_evidence': True,
        'originals_or_specimen_data_manufactured': False,
    })

    prior_paths = ['engineering/engineering-followup-20261030-r12/real-inputs/OEM_DOWNLOAD_ATTEMPTS.json',
                   'engineering/engineering-followup-20261029-r9/real-sources/R9_OEM_SOURCE_APPLICABILITY.json']
    write('CURRENT_INPUT_DELTA.json', {
        'schema': 'r13.actual_input_delta.v1', 'recorded_utc': now,
        'prior_source_identities': [ident(ROOT / p, p) for p in prior_paths],
        'new_same_specimen_originals': 0, 'new_physical_measurements': 0,
        'new_selected_PN_revision_bindings': 0, 'new_complete_OEM_PDF_bytes': 0,
        'new_qualified_original_requirement_ids': [],
        'original_228_required_facts_remain_unsatisfied_by_this_web_work': True,
        'same_specimen_required_count_historical_contract': 207,
        'selected_PN_revision_required_count_historical_contract': 21,
        'physical_identity_part_interface_requirements': {'identity_fields': 10, 'part_roles': 7, 'interfaces': 12},
        'missing_OEM_inputs': ['exact XT2551-3 board/module revision and supplier identity',
                               'selected OLED/touch/COF and finished FPC controlled drawings and stackup',
                               'paired connector PN/revision, orientation, pin-number and terminal/net provenance',
                               'sourced material/process ratings, uncertainty, tolerances and functional evidence'],
        'access_handoff': [
            'Use the manufacturer-linked ReplaceBase document page in an ordinary permitted session; a person must complete any human verification themselves.',
            'iFixit labels complete L3/BOM access as requiring an account; no current authorized account session was accessed.',
            'Even if downloaded, EU/NA literature must be compared against actual XT2551-3 labels and revision before any contract assignment.',
            'Provide original same-specimen photos/labels and exact selected-PN revision documentation; the existing 10/7/12 intake remains the binding contract.'],
        'contact_to_third_parties_sent': False, 'purchases_or_account_changes': False,
        'private_full_copyright_documents_copied_into_public_git': False,
        'all_blockers_closed': False, 'OEM_interconnect_qualified': False,
        'G3_pass': False, 'G4_pass': False, 'G5_pass': False,
        'candidate_go': False, 'fixture_fabrication_go': False, 'manufacturing_go': False,
    })
    shutil.copyfile(HERE / 'fetch_public_document.py', OUT / 'fetch_public_document.py')
    shutil.copyfile(Path(__file__), OUT / 'build_release.py')
    readme = '''# R13：官方维修资料与器件身份的追加核对

本轮新增 **Motorola UK 官方分发路径、三份 EU/系列维修文档的真实索引地址，以及两个官方伙伴的显示总成身份线索**。完整 OEM PDF 实际取得数仍为 **0**；没有新增同样件原件、测量、选定 PN/revision 绑定或实物资格。

## 可核验的进展

[Motorola UK 官方入口](https://en-gb.support.motorola.com/app/right-to-repair)直接将维修文档链接到 [ReplaceBase 文档目录](https://www.replacebase.co.uk/motorola-guide)，并列出 Spares Nordics、MobiParts 等配件伙伴。新定位到以下制造商文档地址。版本按实际可见的文件名记录，未将搜索索引当作完整文件读回。

| 文档 | 已见标识 | 本次访问结论 |
| --- | --- | --- |
| [L2 系列维修手册](https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/XT2551-X_Moto_razr_60_ultra_razr_ultra_Service_and_Repair_Manual_V1.0.pdf) | V1.0；可见主板列表包含 -1/-2/-5/-6 | 定位到索引；未取得完整字节，未证明 -3 适用 |
| [EU L3 手册](https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/XT2551-X_Moto_razr_60_ultra_razr_ultra_Level_3_Service_Manual_for_EU_V1.0.pdf) | EU，V1.0 | 定位到索引；未取得完整字节或准确 variant 范围 |
| [EU 服务 BOM](https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/Phone_Global_SBOM_Moto_razr_60_ultra_razr_ultra_EU_V1.9.pdf) | EU，V1.9 | 实际 GET 为 405、2531-byte Human Verification HTML，非 PDF |

EU BOM 响应的 SHA256 为 `2f086c4e79aa0382057aa19d7f953571738958d42d6bdfbc8b9250722e3a8054`。识别人机验证后停止该站自动下载，没有处理 CAPTCHA、修改访问方式或使用登录凭据。旧 iFixit L3 和 BOM 页面也明确要求账户才能读完整文档；本轮未重试旧 CDN 来规避该要求。原 R12 的三次 HTML 结果保持不变。

## 器件线索及适用性

[Spares 的 Scarab 总成](https://www.spares.se/product/motorola-razr-60-ultra-5g-lcd-display-original-scarab)明示 **XT2551-6 / SKU 5D68C30085**；[MobiParts 的同色服务总成](https://www.mobiparts.ro/spare-parts-motorola/lcd-display-module-for-motorola-razr-60-ultra-sub-inner-pantone-scarab)列出 **5D68C30088、5D68C29813**。这些不同编号没有被解释为等价、可替换或适用于历史 XT2551-3。服务总成名称也不提供裸 OLED、COF 或改造 FPC 的受控叠层。

旧 NA L3 的公开预览提供少量连接器服务编号及针数/间距；具体值及来源放在 `PART_IDENTITY_LEADS.json`。它们只供后续比对标签，未提供同样件的配对插头、端子方向、pinmap 或受控材料/工艺规格。LS Mtron 官方页面已取得 HTML 身份，但未取得明确的 GB35R 原厂受控 PDF；第三方目录数据未作为技术输入采纳。

## 未闭合项目与交接

完整的来源链、文档版本可见范围、实际响应校验分别保存在 `PRIMARY_SOURCE_INDEX.json`、`OEM_SOURCE_APPLICABILITY.json` 和 `ACCESS_READBACK.json`。本目录只含自写源码、少量必要事实、来源链接、HTTP 元数据和 SHA；完整网页/第三方文件正文不在公开清单内。

同样件的 10 个身份字段、7 个实体角色、12 个真实接口仍需原件。原 228 项要求没有因本轮公开资料检索而取得任何合格新增绑定。OLED/COF/FPC、连接器与材料工艺规格仍为 unknown，G3/G4/G5 与制造放行均为 false。确切缺口和允许的下一步在 `CURRENT_INPUT_DELTA.json`，没有代替用户联系供应商、下单、登录或执行设备命令。
'''
    (OUT / 'README.md').write_text(readme)
    files = [ident(p, p.relative_to(OUT).as_posix()) for p in sorted(OUT.rglob('*')) if p.is_file()]
    assert not any(p['path'].lower().endswith(('.pdf', '.html', '.bin')) for p in files)
    write('MANIFEST.json', {'schema': 'r13.public_input_metadata_manifest.v1', 'files': files,
                            'raw_third_party_documents_included': False})
    print(json.dumps({'public_directory': str(OUT), 'files': len(files),
                      'bytes': sum(x['bytes'] for x in files), 'new_complete_PDFs': 0,
                      'new_qualified_specimen_bindings': 0}, indent=2))


if __name__ == '__main__':
    main()

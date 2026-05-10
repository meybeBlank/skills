#!/usr/bin/env python3
"""
Session History Audit - 验证 session-analyzer 输出的完整性
对比 JSONL 原始数据与 HTML 报告，确保无遗漏、无截断
"""

import json
import sys
import re
from pathlib import Path


def load_jsonl(filepath):
    """加载 jsonl，返回 entries 列表"""
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except:
                continue
    return entries


def load_html(filepath):
    """加载 HTML，提取所有 entry 条目"""
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # 提取所有 entry block
    entry_blocks = re.findall(
        r'<div class="entry">\s*<div class="entry-header".*?<div class="entry-body">\s*<pre>(.*?)</pre>',
        html, re.DOTALL
    )
    return html, entry_blocks


def extract_html_entries(html):
    """从 HTML 中提取各类型 entry 的 tag 和 content"""
    results = []
    # 分割每个 entry
    entries_html = re.split(r'<div class="entry">\s*<div class="entry-header"', html)
    for entry_html in entries_html[1:]:  # 跳过第一个空部分
        tag_match = re.search(r'tag\s+(tag-\w+)">(\w+)', entry_html)
        if tag_match:
            tag_class = tag_match.group(1)
            tag_name = tag_match.group(2)
        else:
            tag_name = '???'
            tag_class = ''

        body_match = re.search(r'<div class="entry-body">\s*<pre>(.*?)</pre>', entry_html, re.DOTALL)
        body = body_match.group(1) if body_match else ''
        # HTML 转义还原
        body = body.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&#123;', '{').replace('&#125;', '}').replace('&rarr;', '→').replace('&larr;', '←').replace('&nbsp;', ' ').replace('&#39;', "'").replace('&quot;', '"').strip()

        ts_match = re.search(r'<span class="timestamp">(\d{2}:\d{2}:\d{2})</span>', entry_html)
        timestamp = ts_match.group(1) if ts_match else ''

        results.append({
            'tag': tag_name,
            'tag_class': tag_class,
            'timestamp': timestamp,
            'body': body[:200]  # 截断用于对比
        })
    return results


def audit_user_entries(jsonl_entries, html_entries):
    """审计 USER 条目"""
    issues = []
    passed = []

    # JSONL 中的所有 user entry
    jsonl_users = []
    for i, obj in enumerate(jsonl_entries):
        if obj.get('type') == 'user':
            msg = obj.get('message', {})
            c = msg.get('content', [])
            raw_content = c if isinstance(c, str) else c
            jsonl_users.append((i, raw_content))

    # HTML 中的所有 user entry
    html_users = [e for e in html_entries if e['tag'] == 'USER']
    html_user_bodies = [e['body'] for e in html_users]

    # 检查每个 JSONL user content 是否在 HTML 中
    for i, (line_num, raw_content) in enumerate(jsonl_users):
        user_text = ''
        tool_result = ''

        if isinstance(raw_content, str):
            user_text = raw_content
        elif isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, dict):
                    ct = item.get('type')
                    if ct == 'text':
                        user_text = item.get('text', '')
                        break
                    elif ct == 'tool_result' and not tool_result:
                        tool_result = item.get('content', '')
                elif isinstance(item, str) and not user_text:
                    user_text = item
                    break

        content = user_text if user_text else tool_result
        content_str = str(content).lstrip() if content else ''  # Strip leading whitespace for matching
        # Handle double-escaped HTML entities (content from pasted HTML output)
        content_unescaped = content_str.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&#123;', '{').replace('&#125;', '}').replace('&rarr;', '→').replace('&larr;', '←').replace('&nbsp;', ' ').replace('&#39;', "'").replace('&quot;', '"')
        content_preview = content_unescaped[:200]

        # 在 HTML 中查找匹配（同时搜索原始内容和反转义后的内容）
        found = False
        for hb in html_user_bodies:
            if content_str and len(content_str) > 5:
                # 直接搜索原始字符串在 HTML body 中
                if content_str[:100] in hb or content_str in hb:
                    found = True
                    break
            elif content_str:
                if hb == content_str or content_str in hb:
                    found = True
                    break

        if not found and content_preview and len(content_preview) > 5:
            issues.append({
                'severity': 'WARN',
                'type': 'USER',
                'location': f'JSONL line ~{line_num}',
                'description': f'USER #{i} content not matched in HTML',
                'expected': content_preview[:100],
                'actual': html_user_bodies[i][:100] if i < len(html_user_bodies) else 'N/A'
            })
        elif found:
            passed.append(f'USER #{i}: {content_preview[:60]}')

    return issues, passed


def audit_assistant_entries(jsonl_entries, html_entries):
    """审计 ASSISTANT 条目"""
    issues = []
    passed = []

    # 检查 tool_use 参数是否完整
    for i, obj in enumerate(jsonl_entries):
        if obj.get('type') != 'assistant':
            continue

        msg = obj.get('message', {})
        content_items = msg.get('content', [])

        for item in content_items:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'tool_use':
                name = item.get('name', '')
                inp = item.get('input', {})

                # 检查各工具的关键参数
                if name == 'WebSearch' and 'query' not in inp:
                    issues.append({
                        'severity': 'ERROR',
                        'type': 'tool_use',
                        'location': f'JSONL assistant #{i}',
                        'description': f'{name} missing query parameter',
                        'expected': 'query field present',
                        'actual': 'query field missing'
                    })

                if name == 'WebFetch' and 'url' not in inp:
                    issues.append({
                        'severity': 'ERROR',
                        'type': 'tool_use',
                        'location': f'JSONL assistant #{i}',
                        'description': f'{name} missing url parameter',
                        'expected': 'url field present',
                        'actual': 'url field missing'
                    })

                if name == 'Bash' and 'command' not in inp:
                    issues.append({
                        'severity': 'ERROR',
                        'type': 'tool_use',
                        'location': f'JSONL assistant #{i}',
                        'description': f'{name} missing command parameter',
                        'expected': 'command field present',
                        'actual': 'command field missing'
                    })

    passed.append('Assistant tool_use parameter check passed')

    return issues, passed


def audit_html_content(html_entries):
    """审计 HTML 内容质量"""
    issues = []
    passed = []

    for i, entry in enumerate(html_entries):
        # 检查 CALL 条目是否有参数信息
        if entry['tag'] == 'CALL':
            body = entry['body']
            if '\n' not in body and body.count(':') < 2:
                issues.append({
                    'severity': 'INFO',
                    'type': 'CALL',
                    'location': f'HTML entry #{i}',
                    'description': f'CALL entry may lack parameter details',
                    'expected': 'Contains parameter info (e.g. query=, file_path=)',
                    'actual': body[:100]
                })
            else:
                passed.append(f'CALL #{i}: {body[:60]}')

        # 检查 THINK 条目长度
        if entry['tag'] == 'THINK':
            if len(entry['body']) < 10:
                issues.append({
                    'severity': 'WARN',
                    'type': 'THINK',
                    'location': f'HTML entry #{i}',
                    'description': 'THINK entry appears empty or too short',
                    'expected': 'thinking content present',
                    'actual': entry['body'][:50]
                })
            else:
                passed.append(f'THINK #{i}: {entry["body"][:60]}')

    return issues, passed


def generate_report(jsonl_file, html_file, jsonl_entries, html_entries, html_str):
    """生成审计报告"""

    # 统计
    jsonl_total = len(jsonl_entries)
    jsonl_user = sum(1 for e in jsonl_entries if e.get('type') == 'user')
    jsonl_assistant = sum(1 for e in jsonl_entries if e.get('type') == 'assistant')
    # 统计跳过的条目（file-history-snapshot 且无文件变更）
    jsonl_skipped = sum(1 for e in jsonl_entries
                        if e.get('type') == 'file-history-snapshot'
                        and len(e.get('snapshot', {}).get('trackedFileBackups', {})) == 0)

    html_total = len(html_entries)
    html_user = sum(1 for e in html_entries if e['tag'] == 'USER')
    html_assistant = sum(1 for e in html_entries if e['tag'] in ('CALL', 'TEXT', 'THINK'))

    all_issues = []
    all_passed = []

    # 执行各项审计
    user_issues, user_passed = audit_user_entries(jsonl_entries, html_entries)
    assistant_issues, assistant_passed = audit_assistant_entries(jsonl_entries, html_entries)
    html_issues, html_passed = audit_html_content(html_entries)

    all_issues.extend(user_issues)
    all_issues.extend(assistant_issues)
    all_issues.extend(html_issues)
    all_passed.extend(user_passed)
    all_passed.extend(assistant_passed)
    all_passed.extend(html_passed)

    report = []
    report.append('## 审计报告')
    report.append('')
    report.append(f'**JSONL 文件**: `{jsonl_file}`')
    report.append(f'**HTML 文件**: `{html_file}`')
    report.append('')
    report.append('### 总体结果')
    report.append('')
    report.append(f'| 指标 | JSONL | HTML | 差异 |')
    report.append(f'|------|------|------|------|')
    report.append(f'| 总条目 | {jsonl_total} | {html_total} | {html_total - jsonl_total:+d} |')
    report.append(f'| User | {jsonl_user} | {html_user} | {html_user - jsonl_user:+d} |')
    report.append(f'| Assistant相关 | {jsonl_assistant} | {html_assistant} | — |')
    report.append(f'| 跳过(Skipped) | {jsonl_skipped} | — | (空文件快照) |')
    report.append('')
    # 验证：跳过的 + HTML条数 = JSONL总数
    expected_total = html_total + jsonl_skipped
    if expected_total == jsonl_total:
        report.append(f'✅ **数据完整性验证通过**: HTML条数({html_total}) + 跳过的({jsonl_skipped}) = JSONL总数({jsonl_total})')
    else:
        report.append(f'❌ **数据完整性验证失败**: HTML条数({html_total}) + 跳过的({jsonl_skipped}) ≠ JSONL总数({jsonl_total})，差异: {expected_total - jsonl_total}')
    report.append('')

    # 严重问题
    errors = [i for i in all_issues if i['severity'] == 'ERROR']
    warns = [i for i in all_issues if i['severity'] == 'WARN']
    infos = [i for i in all_issues if i['severity'] == 'INFO']

    if errors:
        report.append('### 发现的问题（ERROR）')
        for issue in errors:
            report.append(f"1. [{issue['severity']}] {issue['type']} @ {issue['location']}: {issue['description']}")
            report.append(f"   - 期望: `{issue['expected']}`")
            report.append(f"   - 实际: `{issue['actual']}`")
        report.append('')

    if warns:
        report.append('### 警告（WARN）')
        for issue in warns:
            report.append(f"1. [{issue['severity']}] {issue['type']} @ {issue['location']}: {issue['description']}")
        report.append('')

    if infos:
        report.append('### 建议（INFO）')
        for issue in infos:
            report.append(f"- {issue['type']} @ {issue['location']}: {issue['description']}")
        report.append('')

    if not errors and not warns:
        report.append('### 通过的项目')
        for p in all_passed[:20]:
            report.append(f'- {p}')
        if len(all_passed) > 20:
            report.append(f'- ... 还有 {len(all_passed) - 20} 项')
        report.append('')

    report.append('### 审计结论')
    if errors:
        report.append(f'❌ **发现 {len(errors)} 个错误，需要修复**')
    elif warns:
        report.append(f'⚠️ **发现 {len(warns)} 个警告**')
    else:
        report.append('✅ **所有审计项目通过**')

    return '\n'.join(report)


def main():
    if len(sys.argv) >= 2:
        jsonl_file = sys.argv[1]
        html_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # 自动查找最新报告
        output_dir = Path(__file__).parent / 'output'
        html_files = list(output_dir.glob('session_history_*.html'))
        if not html_files:
            print('错误: 未找到 HTML 报告文件')
            sys.exit(1)
        html_file = str(sorted(html_files)[-1])
        jsonl_file = None
        print(f'自动使用: {html_file}')

    if not html_file:
        print('错误: 请提供 HTML 文件路径')
        sys.exit(1)

    if not jsonl_file:
        # 从 HTML 文件名推断 jsonl
        base = Path(html_file).stem.replace('session_history_', '')
        jsonl_file = str(Path.home() / '.claude' / 'projects' / '-Users-fengzhen-workspace-SK-simulator' / f'{base}.jsonl')

    if not Path(jsonl_file).exists():
        print(f'错误: JSONL 文件不存在: {jsonl_file}')
        sys.exit(1)

    if not Path(html_file).exists():
        print(f'错误: HTML 文件不存在: {html_file}')
        sys.exit(1)

    print(f'审计中: {jsonl_file} vs {html_file}')

    jsonl_entries = load_jsonl(jsonl_file)
    html_str, html_entries = load_html(html_file)
    html_entry_list = extract_html_entries(html_str)

    report = generate_report(jsonl_file, html_file, jsonl_entries, html_entry_list, html_str)
    print('\n' + report)

    # 保存报告
    skill_dir = Path(__file__).parent
    output_dir = skill_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / 'audit_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'\n报告已保存: {report_file}')

    return report_file


if __name__ == '__main__':
    main()

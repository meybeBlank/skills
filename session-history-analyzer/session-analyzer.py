#!/usr/bin/env python3
"""
Claude Code Session History Analyzer
解析 jsonl 会话记录，生成可折叠 HTML 操作历史
"""

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path


# HTML 样式模板
HTML_HEADER = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Session History - {session_id}</title>
<style>
:root {{
    --bg: #1e1e2e;
    --bg2: #252536;
    --text: #cdd6f4;
    --muted: #6c7086;
    --border: #313244;
    --user-bg: #45475a;
    --think-color: #89b4fa;
    --text-color: #a6e3a1;
    --call-color: #f9e2af;
    --agent-color: #cba6f7;
    --async-border: #b4befe;
    --file-color: #94e2d5;
    --timestamp: #6c7086;
    --tool-result: #fab387;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; background: var(--bg); color: var(--text); min-height: 100vh; padding: 20px; }}
.header {{ text-align: center; margin-bottom: 24px; padding: 20px; background: var(--bg2); border-radius: 12px; border: 1px solid var(--border); }}
.header h1 {{ font-size: 1.4em; color: var(--text); margin-bottom: 8px; }}
.header .meta {{ color: var(--muted); font-size: 0.85em; }}
.timeline {{ max-width: 1400px; margin: 0 auto; padding: 0 16px; }}
.entry {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 6px; overflow: hidden; }}
.entry-header {{ padding: 8px 12px; cursor: pointer; display: flex; align-items: flex-start; gap: 10px; user-select: none; position: sticky; top: 0; background: var(--bg2); z-index: 1; }}
.entry-header:hover {{ background: rgba(255,255,255,0.03); }}
.entry-header .timestamp {{ color: var(--timestamp); font-size: 0.75em; min-width: 70px; flex-shrink: 0; }}
.entry-header .tag {{ font-size: 0.7em; padding: 2px 6px; border-radius: 4px; font-weight: 600; min-width: 60px; text-align: center; flex-shrink: 0; }}
.tag-user {{ background: var(--user-bg); color: var(--text); }}
.tag-think {{ background: rgba(137,180,250,0.15); color: var(--think-color); }}
.tag-text {{ background: rgba(166,227,161,0.15); color: var(--text-color); }}
.tag-call {{ background: rgba(249,226,175,0.15); color: var(--call-color); }}
.tag-agent {{ background: rgba(203,166,247,0.15); color: var(--agent-color); }}
.tag-async {{ background: rgba(180,190,254,0.15); color: var(--async-border); border: 1px solid var(--async-border); }}
.tag-file {{ background: rgba(148,226,213,0.15); color: var(--file-color); }}
.tag-result {{ background: rgba(250,179,135,0.15); color: var(--tool-result); }}
.entry-header .summary {{ flex: 1; color: var(--text); font-size: 0.85em; line-height: 1.4; word-break: break-word; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }}
.entry-header.open .summary {{ display: none; }}
.entry-header .arrow {{ color: var(--muted); transition: transform 0.2s; flex-shrink: 0; margin-top: 1px; }}
.entry-header.open .arrow {{ transform: rotate(90deg); }}
.entry-body {{ display: none; padding: 10px 12px; border-top: 1px solid var(--border); background: rgba(0,0,0,0.2); }}
.entry-body.open {{ display: block; }}
.entry-body pre {{ white-space: pre-wrap; word-break: break-word; font-size: 0.8em; line-height: 1.5; color: var(--text); max-height: none; overflow-x: visible; overflow-y: visible; }}
.stats {{ text-align: center; margin-top: 24px; color: var(--muted); font-size: 0.85em; }}
.filter-bar {{ margin-bottom: 16px; padding: 12px 16px; background: var(--bg2); border-radius: 8px; border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 8px; align-items: center; position: sticky; top: 0; z-index: 100; }}
.filter-bar .filter-label {{ color: var(--muted); font-size: 0.85em; margin-right: 8px; }}
.filter-btn {{ padding: 4px 12px; border-radius: 4px; font-size: 0.8em; cursor: pointer; border: 1px solid var(--border); background: var(--bg); color: var(--text); transition: all 0.2s; }}
.filter-btn:hover {{ background: rgba(255,255,255,0.1); }}
.filter-btn.active {{ background: var(--call-color); color: #1e1e2e; border-color: var(--call-color); }}
.filter-btn[data-tag="USER"].active {{ background: var(--user-bg); border-color: var(--user-bg); }}
.filter-btn[data-tag="THINK"].active {{ background: rgba(137,180,250,0.3); border-color: var(--think-color); }}
.filter-btn[data-tag="CALL"].active {{ background: rgba(249,226,175,0.3); border-color: var(--call-color); }}
.filter-btn[data-tag="TEXT"].active {{ background: rgba(166,227,161,0.3); border-color: var(--text-color); }}
.filter-btn[data-tag="PROG"].active {{ background: rgba(250,179,135,0.3); border-color: var(--tool-result); }}
.filter-btn[data-tag="FILE"].active {{ background: rgba(148,226,213,0.3); border-color: var(--file-color); }}
.filter-btn[data-tag="SYS"].active {{ background: rgba(108,112,134,0.3); border-color: var(--muted); }}
.filter-btn[data-tag="ASYNC"].active {{ background: rgba(180,190,254,0.3); border-color: var(--async-border); }}
.filter-btn[data-tag="LAST"].active {{ background: rgba(180,190,254,0.3); border-color: var(--async-border); }}
.entry.hidden {{ display: none !important; }}
</style>
</head>
<body>
<div class="header">
    <h1>Claude Session History</h1>
    <div class="meta">
        <div>Session: <code>{session_id}</code></div>
        <div>项目: {project}</div>
        <div>分支: {git_branch}</div>
        <div>总条目: {total_entries} | User: {user_count} | Assistant: {assistant_count} | Tool Calls: {tool_count} | Agents: {agent_count}{skipped_text}</div>
    </div>
</div>
<div class="filter-bar">
    <span class="filter-label">筛选:</span>
    <button class="filter-btn active" data-tag="USER">USER</button>
    <button class="filter-btn active" data-tag="THINK">THINK</button>
    <button class="filter-btn active" data-tag="CALL">CALL</button>
    <button class="filter-btn active" data-tag="TEXT">TEXT</button>
    <button class="filter-btn active" data-tag="PROG">PROG</button>
    <button class="filter-btn active" data-tag="FILE">FILE</button>
    <button class="filter-btn active" data-tag="SYS">SYS</button>
    <button class="filter-btn active" data-tag="ASYNC">ASYNC</button>
    <button class="filter-btn active" data-tag="LAST">LAST</button>
</div>
<div class="timeline">
'''

HTML_FOOTER = '''
</div>
<div class="stats">
    Generated by session-history-analyzer | {timestamp}
</div>
<script>
document.querySelectorAll('.entry-header').forEach(h => {{
    h.addEventListener('click', () => {{
        h.classList.toggle('open');
        const body = h.nextElementSibling;
        if (body) body.classList.toggle('open');
    }});
}});
document.querySelectorAll('.filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        const tag = btn.dataset.tag;
        btn.classList.toggle('active');
        const activeTags = new Set(Array.from(document.querySelectorAll('.filter-btn.active')).map(b => b.dataset.tag));
        document.querySelectorAll('.entry').forEach(entry => {{
            const tagSpan = entry.querySelector('.tag');
            if (!tagSpan) return;
            const entryTag = tagSpan.textContent.trim();
            if (activeTags.has(entryTag)) {{
                entry.classList.remove('hidden');
            }} else {{
                entry.classList.add('hidden');
            }}
        }});
    }});
}});
</script>
</body>
</html>
'''

HTML_ENTRY = '''
<div class="entry">
    <div class="entry-header">
        <span class="arrow">&#9658;</span>
        <span class="timestamp">{timestamp}</span>
        <span class="tag {tag_class}">{tag}</span>
        <span class="summary">{summary}</span>
    </div>
    <div class="entry-body">
<pre>{content}</pre>
    </div>
</div>
'''


def get_relative_path(path_str, cwd):
    """将绝对路径转换为相对路径"""
    try:
        cwd_path = Path(cwd)
        full_path = Path(path_str)
        if full_path.is_relative_to(cwd_path):
            return str(full_path.relative_to(cwd_path))
    except:
        pass
    return path_str


def format_time(ts_str):
    """ISO 时间转时:分:秒"""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return ts_str[:19]


def truncate(s, max_len=200, suffix='...'):
    """截断字符串"""
    if s is None:
        return ''
    s = str(s)
    if len(s) <= max_len:
        return s
    return s[:max_len] + suffix


def parse_entry(obj, cwd=''):
    """解析单条 entry，返回 (tag, summary, content, tag_class)"""
    entry_type = obj.get('type', '')
    msg = obj.get('message', {})
    content_items = msg.get('content', [])
    timestamp = format_time(obj.get('timestamp', ''))

    # USER
    if entry_type == 'user':
        raw_content = msg.get('content', [])

        # content 可能是 str 或 list
        # list 中可能混合 tool_result（粘贴的工具输出）和 text（用户输入）
        # 优先取 text 类型，如果没有则取 tool_result
        user_text = ''
        user_tool_result = ''
        if isinstance(raw_content, str):
            user_text = raw_content
        elif isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, dict):
                    ct = item.get('type')
                    if ct == 'text':
                        user_text = item.get('text', '')
                        break
                    elif ct == 'tool_result' and not user_tool_result:
                        user_tool_result = item.get('content', '')
                elif isinstance(item, str) and not user_text:
                    user_text = item
                    break
        # 优先显示用户实际输入，tool_result 作为补充
        user_content = user_text if user_text else user_tool_result
        # 始终返回 USER，即使内容为空（用户按了回车等操作）
        if not user_content:
            return ('USER', '(空)', '', 'tag-user')
        return ('USER', user_content, user_content, 'tag-user')

    # ASSISTANT
    if entry_type == 'assistant':
        thinking = ''
        text_reply = ''
        tool_calls = []

        for item in content_items:
            if not isinstance(item, dict):
                continue
            item_type = item.get('type')
            if item_type == 'thinking':
                thinking = item.get('thinking', '')
            elif item_type == 'text':
                text_reply = item.get('text', '')
            elif item_type == 'tool_use':
                name = item.get('name', '')
                inp = item.get('input', {})
                if name == 'Agent':
                    sub_type = inp.get('subagent_type', '')
                    desc = inp.get('description', '') or inp.get('prompt', '')[:60]
                    tool_calls.append(f"[AGENT] 🤖 [{sub_type}] {desc}")
                elif name == 'Bash':
                    cmd = inp.get('command', '')
                    tool_calls.append(f"[CALL] 🔧 Bash: {cmd}\n    command: {cmd}")
                elif name == 'Read':
                    fp = inp.get('file_path', '')
                    limit = inp.get('limit', '')
                    offset = inp.get('offset', '')
                    tool_calls.append(f"[CALL] 🔧 Read: {get_relative_path(fp, cwd)}\n    file_path={fp} limit={limit} offset={offset}")
                elif name == 'Edit':
                    fp = inp.get('file_path', '')
                    tool_calls.append(f"[CALL] 🔧 Edit: {get_relative_path(fp, cwd)}\n    file_path={fp}")
                elif name == 'Write':
                    fp = inp.get('file_path', '')
                    tool_calls.append(f"[CALL] 🔧 Write: {get_relative_path(fp, cwd)}\n    file_path={fp}")
                elif name == 'Grep':
                    pat = inp.get('pattern', '')
                    path = inp.get('path', '')
                    tool_calls.append(f"[CALL] 🔧 Grep: pattern={pat} path={path}")
                elif name == 'Glob':
                    pat = inp.get('pattern', '')
                    tool_calls.append(f"[CALL] 🔧 Glob: pattern={pat}")
                elif name == 'WebSearch':
                    query = inp.get('query', '')
                    tool_calls.append(f"[CALL] 🔧 WebSearch\n    query=\"{query}\"")
                elif name == 'WebFetch':
                    url = inp.get('url', '')
                    tool_calls.append(f"[CALL] 🔧 WebFetch\n    url={url}")
                elif name == 'AskUserQuestion':
                    tool_calls.append(f"[CALL] 🔧 AskUserQuestion")
                elif name == 'ExitPlanMode':
                    tool_calls.append(f"[CALL] 🔧 ExitPlanMode")
                elif name == 'Skill':
                    skill_name = inp.get('skill', '')
                    args = inp.get('args', '')
                    tool_calls.append(f"[CALL] 🔧 Skill: {skill_name}\n    args={args}")
                elif name in ('EnterPlanMode', 'EnterWorktree', 'ExitWorktree'):
                    tool_calls.append(f"[CALL] 🔧 {name}")
                elif name in ('TaskCreate', 'TaskUpdate', 'TaskGet', 'TaskList'):
                    tool_calls.append(f"[CALL] 🔧 {name}")
                else:
                    tool_calls.append(f"[CALL] 🔧 {name}")

        # 判断主类型
        if thinking and not text_reply and not tool_calls:
            summary = thinking
            content = thinking
            return ('THINK', summary, thinking, 'tag-think')
        elif tool_calls:
            # 显示 tool_use
            call_summary = ' | '.join(tool_calls)
            content_lines = []
            if thinking:
                content_lines.append(f"[思考过程]\n{thinking}")
            for tc in tool_calls:
                content_lines.append(tc)
            return ('CALL', call_summary, '\n'.join(content_lines), 'tag-call')
        elif text_reply:
            return ('TEXT', text_reply, text_reply, 'tag-text')
        else:
            return ('TEXT', '(empty)', '', 'tag-text')

    # FILE-HISTORY-SNAPSHOT
    if entry_type == 'file-history-snapshot':
        backups = obj.get('snapshot', {}).get('trackedFileBackups', {})
        files = list(backups.keys())
        # 使用 snapshot.timestamp 作为时间（entry.timestamp 可能为 None）
        ts = obj.get('timestamp') or obj.get('snapshot', {}).get('timestamp', '')
        timestamp = format_time(ts) if ts else ''
        if len(files) == 0:
            # 无文件变更的快照跳过不显示
            return None
        summary = f"修改了 {len(files)} 个文件: {', '.join([get_relative_path(f, cwd) for f in files])}"
        content_lines = ['[文件变更快照]']
        for fp, info in backups.items():
            rel = get_relative_path(fp, cwd)
            ver = info.get('version', '?')
            btime = info.get('backupTime', '')[:19]
            content_lines.append(f"  {rel} (v{ver}, {btime})")
        return ('FILE', summary, '\n'.join(content_lines), 'tag-file')

    # QUEUE-OPERATION (异步 agent 完成)
    if entry_type == 'queue-operation':
        op = obj.get('operation', '')
        content_raw = obj.get('content', '')
        # 提取 summary
        summary_match = re.search(r'<summary>(.*?)</summary>', content_raw, re.DOTALL)
        summary_text = summary_match.group(1) if summary_match else content_raw[:100]
        usage_match = re.search(r'<total_tokens>(\d+)</total_tokens>.*?<tool_uses>(\d+)</tool_uses>.*?<duration_ms>(\d+)</duration_ms>', content_raw, re.DOTALL)
        if usage_match:
            tokens = int(usage_match.group(1))
            tool_uses = int(usage_match.group(2))
            duration = int(usage_match.group(3))
            extra = f" | {tokens:,} tokens | {tool_uses} tool_calls | {duration/1000:.1f}s"
        else:
            extra = ''
        return ('ASYNC', f"Agent {op}: {summary_text}{extra}", content_raw, 'tag-async')

    # PROGRESS
    if entry_type == 'progress':
        data = obj.get('data', {})
        hook_type = data.get('type', '')
        hook_name = data.get('hookName', '')
        prompt = data.get('prompt', '')
        agent_id = data.get('agentId', '')
        if hook_name:
            # hook_progress 类型
            return ('PROG', hook_name, f"Hook: {hook_name}", 'tag-result')
        elif hook_type == 'agent_progress':
            # agent_progress 类型：显示 agent 任务或响应
            if prompt:
                prompt_preview = prompt[:80].replace('\n', ' ')
                return ('PROG', f"Agent: {prompt_preview}", f"Prompt: {prompt}", 'tag-result')
            elif agent_id:
                # agent 正在执行，显示 agentId
                return ('PROG', f"Agent running: {agent_id[:8]}...", f"AgentId: {agent_id}", 'tag-result')
            else:
                return ('PROG', '(agent_progress)', f"Type: {hook_type}", 'tag-result')
        else:
            return ('PROG', '(progress)', f"Type: {hook_type}", 'tag-result')

    # SYSTEM
    if entry_type == 'system':
        subtype = obj.get('subtype', '')
        return ('SYS', f"System: {subtype}", '', 'tag-result')

    # LAST-PROMPT
    if entry_type == 'last-prompt':
        lp = obj.get('lastPrompt', '')
        return ('LAST', lp, lp, 'tag-result')

    return ('???', entry_type, str(obj), 'tag-result')


def parse_jsonl(filepath):
    """解析 jsonl 文件"""
    entries = []
    stats = {
        'total': 0, 'user': 0, 'assistant': 0, 'tool_calls': 0, 'agents': 0,
        'skipped': 0,
        'session_id': '', 'project': '', 'git_branch': ''
    }

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except:
                continue

            stats['total'] += 1
            entry_type = obj.get('type', '')

            if not stats['session_id']:
                stats['session_id'] = obj.get('sessionId', 'unknown')
            if not stats['project']:
                stats['project'] = obj.get('cwd', '')
            if not stats['git_branch']:
                stats['git_branch'] = obj.get('gitBranch', '')

            if entry_type == 'user':
                stats['user'] += 1
            elif entry_type == 'assistant':
                stats['assistant'] += 1
                # 统计工具调用
                msg = obj.get('message', {})
                for item in msg.get('content', []):
                    if isinstance(item, dict) and item.get('type') == 'tool_use':
                        name = item.get('name', '')
                        stats['tool_calls'] += 1
                        if name == 'Agent':
                            stats['agents'] += 1

            cwd = obj.get('cwd', '')
            result = parse_entry(obj, cwd)
            if result is None:
                stats['skipped'] += 1
                continue  # 跳过不显示的条目（如无文件的 file-history-snapshot）
            tag, summary, content, tag_class = result
            content_str = str(content) if content is not None else ''
            summary_str = str(summary) if summary is not None else ''

            # 构建 HTML
            html_entry = HTML_ENTRY.format(
                timestamp=format_time(obj.get('timestamp', '')),
                tag=tag,
                tag_class=tag_class,
                summary=summary_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('{', '&#123;').replace('}', '&#125;').replace('<style', '&lt;style').replace('</style', '&lt;/style'),
                content=content_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('{', '&#123;').replace('}', '&#125;').replace('<style', '&lt;style').replace('</style', '&lt;/style')
            )
            entries.append(html_entry)

    return entries, stats


def main():
    if len(sys.argv) < 2:
        print("用法: session-analyzer.py <jsonl文件路径>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    # 输出到 skill 目录
    skill_dir = Path(__file__).parent
    output_dir = skill_dir / 'output'
    output_dir.mkdir(exist_ok=True)

    base_name = Path(filepath).stem
    output_html = output_dir / f"session_history_{base_name}.html"

    print(f"解析中: {filepath}")

    entries, stats = parse_jsonl(filepath)

    # 生成 HTML
    skipped_text = f' | Skipped: {stats["skipped"]}' if stats['skipped'] > 0 else ''
    html = HTML_HEADER.format(
        session_id=stats['session_id'][:16],
        project=stats['project'],
        git_branch=stats['git_branch'],
        total_entries=stats['total'],
        user_count=stats['user'],
        assistant_count=stats['assistant'],
        tool_count=stats['tool_calls'],
        agent_count=stats['agents'],
        skipped_text=skipped_text,
    )
    html += '\n'.join(entries)
    html += HTML_FOOTER.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"已生成: {output_html}")
    print(f"  总条目: {stats['total']} | User: {stats['user']} | Assistant: {stats['assistant']} | Tool Calls: {stats['tool_calls']} | Agents: {stats['agents']}")

    return output_html


if __name__ == '__main__':
    main()

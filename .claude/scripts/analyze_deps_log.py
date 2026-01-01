#!/usr/bin/env python3
"""
PME Dependency Log Analyzer

NDJSON 形式のデバッグログを解析し、レイヤ違反・循環・ロード順序をサマリーする。

使用例:
    python analyze_deps_log.py                    # デフォルト: .cursor/debug.log
    python analyze_deps_log.py path/to/debug.log
    python analyze_deps_log.py --json             # JSON形式で出力
    python analyze_deps_log.py --clear            # ログをクリア

出力:
    - レイヤ違反のサマリー（優先度別）
    - 循環検出の詳細（あれば）
    - ロード順序
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Any

# デフォルトのログパス（相対パスで実行されても正しく解決されるよう resolve() を使用）
DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent.parent / ".cursor" / "debug.log"


def parse_ndjson(log_path: Path) -> list[dict]:
    """NDJSON ファイルをパースして辞書のリストを返す"""
    logs = []
    with open(log_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Line {line_num} is not valid JSON: {e}", file=sys.stderr)
    return logs


def extract_violations(logs: list[dict]) -> list[dict]:
    """Layer violations を抽出"""
    for log in logs:
        if log.get("message", "").startswith("Layer violations"):
            return log.get("data", {}).get("violations", [])
    return []


def extract_cycles(logs: list[dict]) -> list[dict]:
    """Topological sort error（循環検出）を抽出"""
    cycles = []
    for log in logs:
        if "Topological sort error" in log.get("message", ""):
            cycles.append(log.get("data", {}))
    return cycles


def extract_load_order(logs: list[dict]) -> list[str]:
    """Final module order を抽出"""
    for log in logs:
        if log.get("message", "").startswith("Final module order"):
            return log.get("data", {}).get("modules", [])
    return []


def extract_mermaid(logs: list[dict]) -> str:
    """Mermaid 依存グラフを抽出"""
    for log in logs:
        if log.get("message", "") == "init_addon dependency graph":
            return log.get("data", {}).get("mermaid", "")
    return ""


def classify_violations(violations: list[dict]) -> dict[str, list[dict]]:
    """違反を優先度別に分類（dependency_cleanup_plan.md に基づく）"""

    # High risk: 触るべきでない領域
    HIGH_RISK_PATTERNS = {
        "runtime", "modal", "handlers", "keymap_helper",
        "previews_helper", "pme.props", "ParsedData"
    }

    # Medium risk: Phase 3 で対処
    MEDIUM_RISK_PATTERNS = {
        "editors → prefs", "editors → operators", "ui → prefs"
    }

    classified = {
        "high": [],
        "medium": [],
        "low": [],
    }

    for v in violations:
        dep = v.get("dependency", "")
        layer_dep = v.get("layer_dependency", "")
        layer_dent = v.get("layer_dependent", "")

        # High risk check
        if any(p in dep for p in HIGH_RISK_PATTERNS):
            classified["high"].append(v)
        # Legacy wrapper は Low risk
        elif layer_dep == "legacy":
            classified["low"].append(v)
        # operators → lower は Medium
        elif layer_dep == "operators":
            classified["medium"].append(v)
        # ui → lower も Medium
        elif layer_dep == "ui" and layer_dent in ("infra", "core"):
            classified["medium"].append(v)
        else:
            classified["low"].append(v)

    return classified


def summarize_by_pattern(violations: list[dict]) -> dict[str, int]:
    """違反を dependency パターンでグループ化してカウント"""
    pattern_counts = defaultdict(int)
    for v in violations:
        dep = v.get("dependency", "unknown")
        # 短縮形に変換 (pie_menu_editor.xxx → xxx)
        short_dep = dep.replace("pie_menu_editor.", "")
        pattern_counts[short_dep] += 1
    return dict(sorted(pattern_counts.items(), key=lambda x: -x[1]))


def format_markdown(
    violations: list[dict],
    classified: dict[str, list[dict]],
    patterns: dict[str, int],
    cycles: list[dict],
    load_order: list[str],
) -> str:
    """結果をマークダウン形式で出力"""
    lines = []
    lines.append("# Dependency Analysis Report\n")

    # サマリー
    lines.append("## Summary\n")
    lines.append(f"- **Total violations**: {len(violations)}")
    lines.append(f"- **High risk**: {len(classified['high'])} (Phase 3+ まで禁止)")
    lines.append(f"- **Medium risk**: {len(classified['medium'])} (Phase 3 で対処)")
    lines.append(f"- **Low risk**: {len(classified['low'])} (Phase 2-B から着手可能)")
    lines.append(f"- **Cycles detected**: {len(cycles)}")
    lines.append("")

    # パターン別カウント
    lines.append("## Violations by Dependency\n")
    lines.append("| Dependency | Count |")
    lines.append("|------------|-------|")
    for dep, count in patterns.items():
        lines.append(f"| `{dep}` | {count} |")
    lines.append("")

    # Low risk の詳細（Phase 2-B で着手可能）
    lines.append("## Low Risk Violations (Phase 2-B Candidates)\n")
    if classified["low"]:
        lines.append("| Dependency | Dependent | Layer Violation |")
        lines.append("|------------|-----------|-----------------|")
        for v in classified["low"]:
            dep = v.get("dependency", "").replace("pie_menu_editor.", "")
            dent = v.get("dependent", "").replace("pie_menu_editor.", "")
            layer = f"{v.get('layer_dependency', '?')} → {v.get('layer_dependent', '?')}"
            lines.append(f"| `{dep}` | `{dent}` | {layer} |")
    else:
        lines.append("*No low-risk violations found.*")
    lines.append("")

    # 循環検出
    if cycles:
        lines.append("## Cycle Detection\n")
        for i, cycle in enumerate(cycles, 1):
            lines.append(f"### Cycle {i}\n")
            lines.append(f"```\n{json.dumps(cycle, indent=2)}\n```\n")

    # ロード順序（折りたたみ）
    lines.append("<details>")
    lines.append("<summary>Module Load Order (click to expand)</summary>\n")
    lines.append("```")
    for i, mod in enumerate(load_order, 1):
        lines.append(f"{i:3}. {mod}")
    lines.append("```")
    lines.append("</details>\n")

    return "\n".join(lines)


def format_json(
    violations: list[dict],
    classified: dict[str, list[dict]],
    patterns: dict[str, int],
    cycles: list[dict],
    load_order: list[str],
) -> str:
    """結果を JSON 形式で出力"""
    result = {
        "summary": {
            "total_violations": len(violations),
            "high_risk": len(classified["high"]),
            "medium_risk": len(classified["medium"]),
            "low_risk": len(classified["low"]),
            "cycles": len(cycles),
        },
        "patterns": patterns,
        "violations": {
            "high": classified["high"],
            "medium": classified["medium"],
            "low": classified["low"],
        },
        "cycles": cycles,
        "load_order": load_order,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def clear_log(log_path: Path) -> None:
    """ログファイルをクリア"""
    log_path.write_text("", encoding="utf-8")
    print(f"Cleared: {log_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="PME Dependency Log Analyzer")
    parser.add_argument("log_path", nargs="?", default=str(DEFAULT_LOG_PATH),
                        help="Path to debug.log (default: .cursor/debug.log)")
    parser.add_argument("--json", action="store_true",
                        help="Output in JSON format")
    parser.add_argument("--clear", action="store_true",
                        help="Clear the log file and exit")
    args = parser.parse_args()

    log_path = Path(args.log_path)

    if args.clear:
        clear_log(log_path)
        return

    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    if log_path.stat().st_size == 0:
        print(f"Warning: Log file is empty: {log_path}", file=sys.stderr)
        print("Run Blender with DBG_DEPS=True and DBG_STRUCTURED=True to generate logs.")
        sys.exit(0)

    # パース
    logs = parse_ndjson(log_path)
    if not logs:
        print("No valid log entries found.", file=sys.stderr)
        sys.exit(1)

    # 抽出
    violations = extract_violations(logs)
    cycles = extract_cycles(logs)
    load_order = extract_load_order(logs)

    # 分類
    classified = classify_violations(violations)
    patterns = summarize_by_pattern(violations)

    # 出力
    if args.json:
        print(format_json(violations, classified, patterns, cycles, load_order))
    else:
        print(format_markdown(violations, classified, patterns, cycles, load_order))


if __name__ == "__main__":
    main()

# infra/debug.py - Debug utilities and logging infrastructure
# LAYER = "infra"
#
# Moved from: debug_utils.py (PME2 layer separation)
# Note: This module is Blender-independent (pure Python)

LAYER = "infra"

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

DBG = False
DBG_INIT = True
DBG_LAYOUT = False
DBG_TREE = False
DBG_CMD_EDITOR = False
DBG_MACRO = False
DBG_STICKY = False
DBG_STACK = False
DBG_PANEL = False
DBG_PM = False
DBG_PROP = False
DBG_PROP_PATH = False

# 新規カテゴリ（後方互換を維持しつつ段階的に使用する）
DBG_DEPS = True      # init_addon の依存解析・ロード順
DBG_PROFILE = True   # 軽量な処理時間計測
DBG_RUNTIME = True   # ランタイム挙動観測（挙動変更はしない）
DBG_STRUCTURED = True  # NDJSON への構造化ログ出力（明示的にオンにする）

# NDJSON 出力先。既定は .cursor/debug.log（存在しない場合は自動作成）
DEBUG_LOG_PATH = Path(__file__).parent.parent / ".cursor" / "debug.log"
DEBUG_SESSION_ID = "pme2-dev"
DEBUG_RUN_ID = "dev"
_DEFAULT_ADDON_ID = Path(__file__).parent.parent.name


def _log(color, *args):
    msg = ""
    for arg in args:
        if msg:
            msg += ", "
        msg += str(arg)
    print(color + msg + '\033[0m')


def logi(*args):
    _log('\033[34m', *args)


def loge(*args):
    _log('\033[31m', *args)


def logh(msg):
    _log('\033[1;32m', "")
    _log('\033[1;32m', msg)


def logw(*args):
    _log('\033[33m', *args)


# --- ここから追加のデバッグ基盤（後方互換を維持したまま拡張） ---

_COLOR_BY_LEVEL = {
    "info": "\033[34m",
    "warn": "\033[33m",
    "error": "\033[31m",
    "success": "\033[1;32m",
}

# 既存フラグをカテゴリにマッピング。新規カテゴリは DBG_* を増やすだけでよい。
_DBG_TABLE = {
    "all": "DBG",
    "init": "DBG_INIT",
    "layout": "DBG_LAYOUT",
    "tree": "DBG_TREE",
    "cmd": "DBG_CMD_EDITOR",
    "macro": "DBG_MACRO",
    "sticky": "DBG_STICKY",
    "stack": "DBG_STACK",
    "panel": "DBG_PANEL",
    "pm": "DBG_PM",
    "prop": "DBG_PROP",
    "prop_path": "DBG_PROP_PATH",
    "deps": "DBG_DEPS",
    "profile": "DBG_PROFILE",
    "runtime": "DBG_RUNTIME",
    "structured": "DBG_STRUCTURED",
}


def set_debug_flag(name: str, value: bool = True) -> None:
    """DBG_* をカテゴリ名または変数名でオン/オフできる簡易ヘルパー。"""
    var_name = _DBG_TABLE.get(name, name)
    if var_name in globals():
        globals()[var_name] = bool(value)


def enabled_categories() -> Tuple[str, ...]:
    """現在有効なカテゴリ名を返す。"""
    return tuple(k for k, v in _DBG_TABLE.items() if globals().get(v, False))


def _is_enabled(category: Optional[str]) -> bool:
    if globals().get("DBG", False):
        return True
    if category is None:
        return False
    return bool(globals().get(_DBG_TABLE.get(category, category), False))


def _emit_structured(
    category: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    *,
    level: str = "info",
    hypothesis_id: Optional[str] = None,
    run_id: Optional[str] = None,
    location: Optional[str] = None,
) -> None:
    """NDJSON に構造化ログを追記する。DBG_STRUCTURED が有効なときのみ動作。"""
    if not globals().get("DBG_STRUCTURED", False):
        return

    payload = {
        "sessionId": DEBUG_SESSION_ID,
        "runId": run_id or DEBUG_RUN_ID,
        "hypothesisId": hypothesis_id or category,
        "category": category,
        "level": level,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }

    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False)
            fp.write("\n")
    except OSError:
        # 構造化ログは観測用途のみ。失敗しても本体挙動には影響させない。
        pass


def dbg_log(
    category: str,
    *args: Any,
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
    hypothesis_id: Optional[str] = None,
    run_id: Optional[str] = None,
    location: Optional[str] = None,
) -> None:
    """カテゴリ付きの軽量ログ。カテゴリが無効なら完全にスキップする。"""
    if not _is_enabled(category):
        return

    color = _COLOR_BY_LEVEL.get(level, "\033[34m")
    _log(color, f"[{category}]", *args)
    _emit_structured(
        category,
        ", ".join(str(a) for a in args),
        data=data,
        level=level,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        location=location,
    )


@contextmanager
def dbg_scope(
    category: str,
    label: str,
    *,
    data: Optional[Dict[str, Any]] = None,
    hypothesis_id: Optional[str] = None,
    run_id: Optional[str] = None,
    location: Optional[str] = None,
):
    """
    軽量なスコープ計測。カテゴリが無効なら NullContext でほぼゼロコスト。
    """
    if not _is_enabled(category):
        yield None
        return

    start = time.perf_counter()
    dbg_log(
        category,
        f"{label}: start",
        data=data,
        hypothesis_id=hypothesis_id,
        run_id=run_id,
        location=location,
        level="info",
    )
    try:
        yield None
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        dbg_log(
            category,
            f"{label}: end ({elapsed_ms:.2f} ms)",
            data={"elapsed_ms": elapsed_ms, **(data or {})},
            hypothesis_id=hypothesis_id,
            run_id=run_id,
            location=location,
            level="info",
        )


class DependencyGraphLogger:
    """
    init_addon などのロード順・依存関係をテキスト/mermaid で吐き出すヘルパー。
    """

    def __init__(self, name: str = "init_addon"):
        self.name = name
        self._edges: list[Tuple[str, str, Optional[str]]] = []
        self._nodes: set[str] = set()

    def add(self, src: str, dst: str, label: Optional[str] = None) -> None:
        self._nodes.add(src)
        self._nodes.add(dst)
        self._edges.append((src, dst, label))

    def add_chain(self, nodes: Iterable[str], label: Optional[str] = None) -> None:
        prev = None
        for node in nodes:
            if prev is not None:
                self.add(prev, node, label)
            prev = node

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        for node in sorted(self._nodes):
            lines.append(f'    "{node}"')
        for src, dst, label in self._edges:
            if label:
                lines.append(f'    "{src}" -->|{label}| "{dst}"')
            else:
                lines.append(f'    "{src}" --> "{dst}"')
        return "\n".join(lines)

    def flush(
        self,
        category: str = "deps",
        *,
        message: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
        run_id: Optional[str] = None,
        location: Optional[str] = None,
    ) -> None:
        if not _is_enabled(category):
            return

        mermaid = self.to_mermaid()
        dbg_log(
            category,
            message or f"{self.name} dependency graph",
            data={"mermaid": mermaid},
            hypothesis_id=hypothesis_id,
            run_id=run_id,
            location=location,
            level="info",
        )
        # 視認性のためヘッダ＋本体をまとめて出力
        logh(message or f"{self.name} dependency graph")
        _log("\033[34m", mermaid)


def make_edges_from_graph(graph: Dict[str, Iterable[str]]) -> list[Tuple[str, str]]:
    """
    依存グラフ（dependency -> dependents セット）を edge リストに変換。
    """
    edges: list[Tuple[str, str]] = []
    for dep, dependents in graph.items():
        for mod in dependents:
            edges.append((dep, mod))
    return edges


_LAYER_ORDER = {
    "core": 0,
    "infra": 1,
    "ui": 2,
    "editors": 3,
    "operators": 4,
    "prefs": 5,
    "root": 6,      # __init__.py 相当
    "legacy": 7,    # 旧構成（暫定で最下位に置く）
}

# Facade modules: Can be imported from any layer except core.
# See architecture.md section 5.2 for details.
# These modules don't have LAYER constants because they are cross-cutting.
_FACADE_MODULES = {"addon"}


def _is_facade_module(module_name: str, addon_id: Optional[str] = None) -> bool:
    """Check if the module is a facade module (e.g., addon)."""
    addon_prefix = addon_id or _DEFAULT_ADDON_ID
    # Check for exact match: pie_menu_editor.addon
    for facade in _FACADE_MODULES:
        if module_name == f"{addon_prefix}.{facade}":
            return True
    return False


def resolve_layer(
    module_name: str,
    addon_id: Optional[str] = None,
    *,
    module: Optional[Any] = None,
) -> Optional[str]:
    """
    モジュールのレイヤを判定する。判定優先順位:

    1. module オブジェクトが渡された場合、その LAYER 定数を最優先で使用
    2. sys.modules にモジュールがある場合、その LAYER 定数を使用
    3. パスパターン（core./ui./infra./...）から推定
    4. 上記すべて該当しない場合は "legacy"

    例: pie_menu_editor.core.foo -> core
        pie_menu_editor.bl_utils (LAYER="infra") -> infra
    """
    import sys

    addon_prefix = addon_id or _DEFAULT_ADDON_ID

    # 1. 明示的に渡された module オブジェクトから LAYER を取得
    if module is not None:
        layer = getattr(module, "LAYER", None)
        if layer and layer in _LAYER_ORDER:
            return layer

    # 2. sys.modules から LAYER 定数を取得（既にインポート済みの場合）
    if module_name in sys.modules:
        mod = sys.modules[module_name]
        layer = getattr(mod, "LAYER", None)
        if layer and layer in _LAYER_ORDER:
            return layer

    # 3. パスパターンから推定
    if module_name == addon_prefix:
        return "root"

    prefix = f"{addon_prefix}."
    if module_name.startswith(prefix):
        head = module_name[len(prefix) :].split(".", 1)[0]
        if head in _LAYER_ORDER:
            return head
        # パスで判定できない → legacy
        return "legacy"

    # addon 外のモジュール
    return None


def detect_layer_violations(
    edges: Iterable[Tuple[str, str]],
    *,
    addon_id: Optional[str] = None,
) -> list[Dict[str, Any]]:
    """
    依存方向がレイヤ規約（上位→下位 OK, 下位→上位 NG）に反していないかを検出。
    edges: (dependency, dependent) のタプル列。

    特例:
    - Facade modules (addon) は core 以外からインポート可能。
      See architecture.md section 5.2.
    """
    violations = []
    for dep, mod in edges:
        # Facade module exception: addon can be imported from any layer except core
        if _is_facade_module(dep, addon_id):
            l_mod = resolve_layer(mod, addon_id)
            if l_mod != "core":
                continue  # Allowed: non-core importing from facade

        l_dep = resolve_layer(dep, addon_id)
        l_mod = resolve_layer(mod, addon_id)
        if l_dep is None or l_mod is None:
            continue
        rank_dep = _LAYER_ORDER.get(l_dep, 99)
        rank_mod = _LAYER_ORDER.get(l_mod, 99)
        # dependent が依存先より「上位レイヤ」であれば違反
        if rank_mod < rank_dep:
            violations.append(
                {
                    "dependency": dep,
                    "dependent": mod,
                    "layer_dependency": l_dep,
                    "layer_dependent": l_mod,
                }
            )
    return violations


def log_layer_violations(
    edges: Iterable[Tuple[str, str]],
    *,
    addon_id: Optional[str] = None,
    category: str = "deps",
    location: Optional[str] = None,
    run_id: Optional[str] = None,
) -> None:
    """
    レイヤ違反を検出してログ出力する。カテゴリ無効時は完全スキップ。

    出力フォーマット (違反がある場合):
        [deps] Layer violations: 3
        [deps]   infra <- ui : bl_utils.py imports from ui/__init__.py
        [deps]   core <- editors : pme_types.py imports from editors/base.py
    """
    if not _is_enabled(category):
        return

    violations = detect_layer_violations(edges, addon_id=addon_id)
    if not violations:
        dbg_log(
            category,
            "Layer check: OK",
            data={"checked_edges": len(list(edges)) if not isinstance(edges, list) else len(edges)},
            location=location,
            run_id=run_id,
        )
        return

    # ヘッダー出力
    dbg_log(
        category,
        f"Layer violations: {len(violations)}",
        data={"violations": violations},
        level="warn",
        location=location,
        run_id=run_id,
    )

    # 各違反を読みやすい形式で出力
    # フォーマット: layer_dependent <- layer_dependency : dependent imports dependency
    for v in violations:
        l_dep = v["layer_dependency"]
        l_mod = v["layer_dependent"]
        dep_short = v["dependency"].split(".")[-1]
        mod_short = v["dependent"].split(".")[-1]
        _log(
            "\033[33m",  # yellow/warn
            f"  {l_mod} <- {l_dep} : {mod_short} imports {dep_short}",
        )


# ======================================================
# 出力改善用ヘルパー関数
# ======================================================

def print_section_header(title: str) -> None:
    """セクションヘッダーを出力する。"""
    print()
    print(f"\033[1;36m{'=' * 50}\033[0m")
    print(f"\033[1;36m  {title}\033[0m")
    print(f"\033[1;36m{'=' * 50}\033[0m")


def print_subsection_header(title: str) -> None:
    """サブセクションヘッダーを出力する。"""
    print()
    print(f"\033[1;33m--- {title} ---\033[0m")


def print_success(message: str) -> None:
    """成功メッセージを出力する。"""
    print(f"\033[32m✓ {message}\033[0m")


def print_failure(message: str) -> None:
    """失敗メッセージを出力する。"""
    print(f"\033[31m✗ {message}\033[0m")


def print_numbered_list(
    items: Iterable[str],
    *,
    short_name_func: Optional[callable] = None,
    deps_dict: Optional[Dict[str, Iterable[str]]] = None,
) -> None:
    """
    番号付きリストを出力する。

    Args:
        items: 出力するアイテムのリスト
        short_name_func: モジュール名を短縮する関数（省略時はそのまま出力）
        deps_dict: 依存関係の辞書（キー: モジュール、値: 依存先のセット）
    """
    for i, item in enumerate(items, 1):
        name = short_name_func(item) if short_name_func else item
        if deps_dict and item in deps_dict:
            deps = deps_dict[item]
            if deps:
                dep_names = ", ".join(
                    short_name_func(d) if short_name_func else d
                    for d in sorted(deps)[:3]  # 最大3件表示
                )
                if len(deps) > 3:
                    dep_names += f" +{len(deps) - 3}"
                print(f"  {i:2d}. {name} \033[90m(→ {dep_names})\033[0m")
            else:
                print(f"  {i:2d}. {name}")
        else:
            print(f"  {i:2d}. {name}")

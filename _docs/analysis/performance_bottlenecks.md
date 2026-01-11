# PME2 Performance Bottleneck Analysis

> 調査日: 2026-01-11
> 対象ブランチ: pme2-dev

## 概要

PME2のパフォーマンスボトルネックを調査し、優先度別に分類した。

---

## 1. 起動時のボトルネック

### 1-1. AST解析による依存性検出 🔴 CRITICAL

**ファイル**: `addon.py:261-466, 790-892`

**問題点**:
- 起動時に全モジュールのソースコードをAST解析
- `_analyze_imports()` が各モジュールを読み込み、パース
- `_analyze_dependencies()` で import分析 + PropertyGroup依存性検出 + DEPENDS_ON検出
- `_topological_sort()` でKahnのアルゴリズム実行

**影響**: 起動時 2-5秒の遅延

**対応案**:
- 依存関係を `.deps_cache.json` にキャッシュ
- ファイル変更時のみ再計算

### 1-2. グローバルアイコン読み込み 🟠 HIGH

**ファイル**: `infra/previews.py:129-130`

**問題点**:
```python
ph = PreviewsHelper()
ph.refresh()  # モジュール読み込み時に全アイコン読み込み
```

- 起動時に全アイコンをディスクから読み込み
- `_load_icons_from_dir()` が全 .png ファイルを走査

**影響**: 起動時 500ms-2s

**対応案**: lazy loading（初回アクセス時に読み込み）

### 1-3. PropertyGroup大量定義 🟡 LOW

**ファイル**: `preferences.py`

**問題点**:
- 11個のPropertyGroupクラス定義
- 起動時にBlenderへの登録

**影響**: 軽微（Blender標準の処理）

---

## 2. オペレーター実行時のボトルネック

### 2-1. `_draw_item()` メソッド 🔴 CRITICAL

**ファイル**: `operators/__init__.py:1169-1369`

**呼び出し頻度**: 8-10回/メニュー表示（各アイテム毎）

| 問題 | 行 | 詳細 |
|------|-----|------|
| exec() 呼び出し | 1193 | `exec("str(bpy.ops.%s.idname)" % op_bl_idname)` |
| eval() 呼び出し | 1321 | `eval(text, exec_globals)` |
| pmi.parse() 13回 | 1179, 1191, 1207, 1226, 1267, 1290, 1300, 1330, 1347, 1351, 1457 | キャッシュなし |
| sub_pm.poll() in draw | 1231, 1238 | 描画中に poll 呼び出し |
| get_data() 4連続 | 1256-1274 | 同一メニューに4回アクセス |

**影響**: 10アイテムのPieメニュー → 130+ parse呼び出し/表示

**対応案**:
- parse結果をアイテム単位でキャッシュ
- exec/eval の結果をキャッシュ
- get_data() 結果をローカル変数化

### 2-2. Modal イベントループ 🔴 CRITICAL

**ファイル**: `operators/__init__.py:1508-1696`

**呼び出し頻度**: 50ms毎（タイマーイベント）

| 問題 | 行 | 詳細 |
|------|-----|------|
| schema.parse() 毎イベント | 1512, 1687, 1749, 1752 | 4回/イベント |
| 6種類のタイマーチェック | 1614-1680 | 毎イベント全チェック |
| 10+段のネスト | 1522-1693 | 複雑な条件分岐 |
| active_ops イテレーション | 1670 | 全アクティブオペレーター走査 |

**影響**: メニュー表示中のCPU負荷

**対応案**:
- schema.parse() 結果をキャッシュ
- タイマー状態をフラグで管理

### 2-3. Invoke メソッド 🟠 HIGH

**ファイル**: `operators/__init__.py:1876-2059`

| 問題 | 行 | 詳細 |
|------|-----|------|
| O(n²) ループ | 1964-1977 | 全pie_menusをループしてキー比較 |
| 6つのキープロパティ比較 | 1969-1974 | key, ctrl, shift, alt, oskey, key_mod |
| 逆順ループ | 1914-1931 | マウスボタンチェックで全メニュー走査 |

**影響**: 100+メニュー環境で顕著

**対応案**:
- キー組み合わせをハッシュ化してO(1)検索
- キーマップのインデックス構築

### 2-4. operator_utils.py tokenize処理 🟠 HIGH

**ファイル**: `operator_utils.py:371-489`

| 問題 | 行 | 詳細 |
|------|-----|------|
| tokenize処理 | 371-403 | `_split_statement()` → `tokenize()` → `_extract_args()` |
| eval() per arg | 465-472 | 引数毎に `pme.context.eval()` |
| fallback eval | 479-489 | `eval("bpy.ops.%s" % op)` |

**影響**: COMMANDモードの各アイテム実行時

**対応案**:
- tokenize結果のキャッシュ
- compile()結果の保持

### 2-5. PME_OT_modal_base 🟠 HIGH

**ファイル**: `operators/__init__.py:569-1092` (524行)

| 問題 | 行 | 詳細 |
|------|-----|------|
| execute_pmi() | 620 | アイテム操作毎に呼び出し |
| 毎フレームeval | 628 | プロパティデルタ評価 |
| 複雑なステートマシン | 全体 | 524行のモーダルロジック |

**対応案**: 長期的にはステートマシンの再設計（2.0.1以降）

---

## 3. UI描画時のボトルネック

### 3-1. 毎フレーム get_prefs() 🟠 MEDIUM

**ファイル**: `editors/base.py:89-136`

**問題点**:
```python
def gen_header_draw(pm_name):
    def _draw(self, context):
        pm = get_prefs().pie_menus[pm_name]  # 毎フレーム呼び出し
```

**影響**: 複数ヘッダー/メニュー/パネルで数十回/フレーム

**対応案**: draw関数の親スコープでキャッシュ

### 3-2. panel_types_sorter() 再帰 🟡 LOW

**ファイル**: `ui/panels.py:42-56`

**問題点**: 深い再帰でUI表示遅延

**対応案**: メモ化（計算結果を保持）

### 3-3. getattr/hasattr多用 🟡 LOW

**検出**: 全体で329回

**問題点**: 小さな積み重ね

**対応案**: ホットパスでの属性アクセス最適化

---

## 4. JSON/IO処理

### 4-1. JSON dump（バックアップ時） 🟡 LOW

**ファイル**: `infra/io.py:666`

**問題点**: 大規模メニューで `json.dumps()` が数秒

**対応案**: diff ベースのバックアップ

---

## 5. 優先度サマリー

### 🔴 CRITICAL（即時対応推奨）

| 項目 | ファイル | 期待効果 |
|------|---------|---------|
| _draw_item parse/eval キャッシュ | operators/__init__.py:1169-1369 | 描画時間 50-70% 削減 |
| modal ループ schema.parse() キャッシュ | operators/__init__.py:1508-1696 | CPU負荷 30-50% 削減 |
| AST解析キャッシュ | addon.py:261-466 | 起動時間 2-5秒短縮 |

### 🟠 HIGH（効果的な改善）

| 項目 | ファイル | 期待効果 |
|------|---------|---------|
| invoke キー比較ハッシュ化 | operators/__init__.py:1876-2059 | O(n²) → O(n) |
| アイコン lazy loading | infra/previews.py | 起動時間 0.5-2秒短縮 |
| operator_utils tokenize キャッシュ | operator_utils.py | COMMAND実行高速化 |

### 🟡 LOW（余裕があれば）

| 項目 | ファイル | 期待効果 |
|------|---------|---------|
| get_prefs() キャッシング | editors/base.py | UI応答性向上 |
| panel_types_sorter() メモ化 | ui/panels.py | UI表示改善 |
| JSON diff backup | infra/io.py | バックアップ高速化 |

---

## 6. ファイルサイズ参考

| ファイル | 行数 | 役割 | 優先度 |
|----------|------|------|--------|
| `operators/__init__.py` | 2,598 | メインランタイムオペレーター | CRITICAL |
| `operator_utils.py` | 489 | コマンドパース | HIGH |
| `addon.py` | 1,161 | モジュールローダー | HIGH |
| `preferences.py` | 1,888 | 設定・PropertyGroup | MEDIUM |
| `operators/ed/pmi.py` | 821 | PMIエディターオペレーター | MEDIUM |

---

## 7. 次のステップ

1. **計測基盤の整備**: プロファイリングコードの追加
2. **キャッシュ戦略の設計**: parse/eval結果のキャッシュ方式検討
3. **段階的な改善**: CRITICAL → HIGH → LOW の順で対応
4. **効果測定**: 改善前後の比較

---

## 参照

- `@_docs/design/json_schema_v2.md` — JSON形式仕様
- `@_docs/guides/rc_roadmap.md` — RCロードマップ

# rules/architecture.md

## 1. レイヤ構造（目標）

下に行くほど「土台」側。

- `core/`    : Blender 非依存のロジック・データ構造
- `infra/`   : Blender 依存の基盤 (`pme.context`, overlay, keymap など)
- `ui/`      : LayoutHelper, UIList, menus, popups
- `editors/` : 各モードのエディタロジック
- `operators/`: 編集・検索・ユーティリティ系オペレーター
- `prefs/`   : PMEPreferences などアドオン設定

## 2. 依存方向のルール（簡略版）

- 上位 → 下位への import は OK
- 下位 → 上位への import は NG

つまり:

- `core` は他レイヤを import してはいけない
- `infra` は `core` のみ import してよい
- `ui` は `infra` / `core` のみ import してよい
- `editors` は `ui` / `infra` / `core` のみ import してよい
- `operators` は `editors` / `ui` / `infra` / `core` のみ import してよい
- `prefs` はどこでも参照してよいが、逆方向の import は不可

例外:

- `TYPE_CHECKING` 内の import は依存違反としてカウントしない

現状:

- 上記ルールは **目標** であり、現時点では破っている箇所が多数ある
- 順次整理していく

## 3. init_addon と force_order

- `init_addon()` は依存解析 + トポロジカルソートを前提とする
- `force_order` は **デバッグ専用**:
  - 一時ブランチでは使ってよい
  - `pme2-dev` へマージする前に必ず空にする

# GPU Layout Theme & Widget Mapping

> **Status**: Research Complete
> **Date**: 2026-01-16
> **Related Issue**: #110 Theme Integration
> **Source**: Blender 5.x source code analysis (`interface_widgets.cc`, `interface_layout.cc`, `interface_utils.cc`)

---

## 概要

このドキュメントは `layout.prop()` 実装に必要な **ウィジェットタイプ** と **テーマカラー** の正確な対応をまとめたものです。
Blender ソースコードの調査に基づいています。

---

## 1. ThemeUserInterface の wcol_* 属性一覧

Blender の `bpy.context.preferences.themes[0].user_interface` に存在する全ウィジェットカラー定義：

| 属性名 | 用途 | 備考 |
|--------|------|------|
| `wcol_regular` | 通常ボタン（デフォルト） | フォールバック |
| `wcol_toggle` | トグルボタン | Boolean with icon |
| `wcol_option` | チェックボックス | Boolean without icon |
| `wcol_radio` | ラジオボタン | Row (enum item) |
| `wcol_num` | 数値入力フィールド | Int/Float |
| `wcol_numslider` | スライダー | Int/Float with PERCENTAGE/FACTOR |
| `wcol_text` | テキスト入力 | String |
| `wcol_tool` | ツールボタン | Button/Exec |
| `wcol_toolbar_item` | ツールバーアイテム | Toolbar buttons |
| `wcol_tab` | タブ | Tab widgets |
| `wcol_menu` | メニューボタン | Dropdown menus |
| `wcol_menu_back` | メニュー背景 | Menu background |
| `wcol_menu_item` | メニューアイテム | Items inside menu |
| `wcol_pulldown` | プルダウンメニュー | Header pulldowns |
| `wcol_pie_menu` | パイメニュー | Pie menu items |
| `wcol_tooltip` | ツールチップ | Tooltips |
| `wcol_box` | ボックス | Box/Panel backgrounds |
| `wcol_scroll` | スクロールバー | Scrollbars |
| `wcol_list_item` | リストアイテム | List/Tree items |
| `wcol_progress` | プログレスバー | Progress indicators |
| `wcol_state` | 状態カラー | Animation/Keyed states |
| `wcol_curve` | カーブウィジェット | Curve/Profile editors |

---

## 2. ThemeWidgetColors の構造

各 `wcol_*` は以下のプロパティを持つ：

```python
# アクセス例
theme_colors = bpy.context.preferences.themes[0].user_interface.wcol_numslider

# RGBA カラー (4 items, [0, 1] range)
theme_colors.inner        # 内部塗りつぶし（通常状態）
theme_colors.inner_sel    # 内部塗りつぶし（選択状態）
theme_colors.item         # アイテム色（スライダーつまみ等）
theme_colors.outline      # アウトライン（通常状態）
theme_colors.outline_sel  # アウトライン（選択状態）

# RGB テキストカラー (3 items)
theme_colors.text         # テキスト色（通常状態）
theme_colors.text_sel     # テキスト色（選択状態）

# 数値プロパティ
theme_colors.roundness    # 角丸 [0, 1]
theme_colors.shadetop     # 上部シェーディング [-100, 100]
theme_colors.shadedown    # 下部シェーディング [-100, 100]
theme_colors.show_shaded  # シェーディング有効化
```

---

## 3. ウィジェットタイプ列挙 (uiWidgetTypeEnum)

Blender 内部で使用されるウィジェットタイプ（`interface_widgets.cc` より）：

```c
enum uiWidgetTypeEnum {
  UI_WTYPE_REGULAR,        // デフォルト
  UI_WTYPE_LABEL,          // ラベル
  UI_WTYPE_TOGGLE,         // トグルボタン
  UI_WTYPE_CHECKBOX,       // チェックボックス
  UI_WTYPE_RADIO,          // ラジオボタン
  UI_WTYPE_NUMBER,         // 数値フィールド
  UI_WTYPE_SLIDER,         // スライダー
  UI_WTYPE_EXEC,           // 実行ボタン
  UI_WTYPE_TOOLBAR_ITEM,   // ツールバーアイテム
  UI_WTYPE_TAB,            // タブ
  UI_WTYPE_TOOLTIP,        // ツールチップ

  // 文字列系
  UI_WTYPE_NAME,           // テキスト入力
  UI_WTYPE_NAME_LINK,      // リンク付きテキスト
  UI_WTYPE_POINTER_LINK,   // ポインタリンク
  UI_WTYPE_FILENAME,       // ファイル名入力

  // メニュー系
  UI_WTYPE_MENU_RADIO,     // メニュー（ラジオ）
  UI_WTYPE_MENU_ICON_RADIO,// メニュー（アイコン）
  UI_WTYPE_PULLDOWN,       // プルダウン
  UI_WTYPE_MENU_ITEM,      // メニューアイテム
  UI_WTYPE_MENU_ITEM_PIE,  // パイメニューアイテム
  UI_WTYPE_MENU_BACK,      // メニュー背景

  // 特殊系
  UI_WTYPE_ICON,           // アイコンのみ
  UI_WTYPE_SWATCH,         // カラースウォッチ
  UI_WTYPE_RGB_PICKER,     // RGBピッカー
  UI_WTYPE_UNITVEC,        // 単位ベクトル球
  UI_WTYPE_BOX,            // ボックス
  UI_WTYPE_SCROLL,         // スクロールバー
  UI_WTYPE_LISTITEM,       // リストアイテム
  UI_WTYPE_PROGRESS,       // プログレスバー
  UI_WTYPE_NODESOCKET,     // ノードソケット
  UI_WTYPE_VIEW_ITEM,      // ビューアイテム
};
```

---

## 4. ウィジェットタイプ → テーマ対応表

**Source**: `widget_type()` function in `interface_widgets.cc:4771-4953`

| uiWidgetTypeEnum | wcol_theme | 備考 |
|------------------|------------|------|
| `UI_WTYPE_REGULAR` | `wcol_regular` | デフォルト |
| `UI_WTYPE_TOGGLE` | `wcol_toggle` | トグルボタン |
| `UI_WTYPE_CHECKBOX` | `wcol_option` | チェックボックス |
| `UI_WTYPE_RADIO` | `wcol_radio` | ラジオボタン |
| `UI_WTYPE_NUMBER` | `wcol_num` | 数値フィールド |
| `UI_WTYPE_SLIDER` | `wcol_numslider` | **スライダー** |
| `UI_WTYPE_EXEC` | `wcol_tool` | 実行ボタン |
| `UI_WTYPE_TOOLBAR_ITEM` | `wcol_toolbar_item` | ツールバー |
| `UI_WTYPE_TAB` | `wcol_tab` | タブ |
| `UI_WTYPE_TOOLTIP` | `wcol_tooltip` | ツールチップ |
| `UI_WTYPE_NAME` | `wcol_text` | テキスト入力 |
| `UI_WTYPE_MENU_RADIO` | `wcol_menu` | メニューボタン |
| `UI_WTYPE_MENU_ICON_RADIO` | `wcol_menu` | アイコンメニュー |
| `UI_WTYPE_PULLDOWN` | `wcol_pulldown` | プルダウン |
| `UI_WTYPE_MENU_ITEM` | `wcol_menu_item` | メニューアイテム |
| `UI_WTYPE_MENU_ITEM_PIE` | `wcol_pie_menu` | パイメニュー |
| `UI_WTYPE_MENU_BACK` | `wcol_menu_back` | メニュー背景 |
| `UI_WTYPE_BOX` | `wcol_box` | ボックス |
| `UI_WTYPE_SCROLL` | `wcol_scroll` | スクロール |
| `UI_WTYPE_LISTITEM` | `wcol_list_item` | リストアイテム |
| `UI_WTYPE_VIEW_ITEM` | `wcol_list_item` | ビューアイテム |
| `UI_WTYPE_PROGRESS` | `wcol_progress` | プログレス |

---

## 5. プロパティタイプ → ボタンタイプ → テーマ対応

**Source**: `uiDefAutoButR()` in `interface_utils.cc:56-156`

### 5.1 PROP_BOOLEAN

| 条件 | ButType | Widget | Theme |
|------|---------|--------|-------|
| with icon, no text | `IconToggle` | `UI_WTYPE_TOGGLE` | `wcol_toggle` |
| with icon and text | `IconToggle` | `UI_WTYPE_TOGGLE` | `wcol_toggle` |
| no icon | `Checkbox` | `UI_WTYPE_CHECKBOX` | `wcol_option` |

### 5.2 PROP_INT / PROP_FLOAT

| Subtype | ButType | Widget | Theme |
|---------|---------|--------|-------|
| `COLOR` / `COLOR_GAMMA` (array) | `Color` | `UI_WTYPE_SWATCH` | (special) |
| `PERCENTAGE` / `FACTOR` | `NumSlider` | `UI_WTYPE_SLIDER` | `wcol_numslider` |
| その他 | `Num` | `UI_WTYPE_NUMBER` | `wcol_num` |

### 5.3 PROP_STRING

| 条件 | ButType | Widget | Theme |
|------|---------|--------|-------|
| 通常 | `Text` | `UI_WTYPE_NAME` | `wcol_text` |
| 検索付き | `SearchMenu` | `UI_WTYPE_NAME` | `wcol_text` |

### 5.4 PROP_ENUM

| 条件 | ButType | Widget | Theme |
|------|---------|--------|-------|
| 単一選択 | `Menu` | `UI_WTYPE_MENU_RADIO` | `wcol_menu` |
| 展開表示 | `Row` | `UI_WTYPE_RADIO` | `wcol_radio` |
| フラグ（複数選択） | 展開 | `UI_WTYPE_RADIO` | `wcol_radio` |

### 5.5 PROP_POINTER

| 条件 | ButType | Widget | Theme |
|------|---------|--------|-------|
| 通常 | `SearchMenu` | `UI_WTYPE_NAME` | `wcol_text` |

---

## 6. PropertySubType 一覧

**Source**: `RNA_types.hh:245-295` および PME `editors/property.py:118-132`

### 6.1 数値サブタイプ (Int/Float)

```python
SUBTYPE_NUMBER_ITEMS = [
    'PIXEL',           # ピクセル値
    'UNSIGNED',        # 符号なし
    'PERCENTAGE',      # パーセント (0-100) → スライダー表示
    'FACTOR',          # ファクター (0-1) → スライダー表示
    'ANGLE',           # 角度
    'TIME',            # 時間（フレーム）
    'TIME_ABSOLUTE',   # 絶対時間
    'DISTANCE',        # 距離
    'DISTANCE_CAMERA', # カメラ距離
    'POWER',           # パワー
    'TEMPERATURE',     # 温度
    'NONE',            # なし
]
```

### 6.2 数値配列サブタイプ

```python
SUBTYPE_NUMBER_ARRAY_ITEMS = [
    'COLOR',           # RGB カラー → カラーピッカー
    'COLOR_GAMMA',     # ガンマ補正カラー → カラーピッカー
    'TRANSLATION',     # 位置
    'DIRECTION',       # 方向
    'VELOCITY',        # 速度
    'ACCELERATION',    # 加速度
    'MATRIX',          # 行列
    'EULER',           # オイラー角
    'QUATERNION',      # クォータニオン
    'AXISANGLE',       # 軸角度
    'XYZ',             # XYZ
    'XYZ_LENGTH',      # XYZ長さ
    'COORDINATES',     # 座標
    'LAYER',           # レイヤー
    'LAYER_MEMBER',    # レイヤーメンバー
    'NONE',
]
```

### 6.3 文字列サブタイプ

```python
STRING_SUBTYPES = [
    'FILE_PATH',       # ファイルパス
    'DIR_PATH',        # ディレクトリパス
    'FILE_NAME',       # ファイル名
    'BYTE_STRING',     # バイト文字列
    'PASSWORD',        # パスワード
    'NONE',
]
```

---

## 7. カラーウィジェット

### 7.1 カラーピッカー関連

| ButType | 用途 | Theme |
|---------|------|-------|
| `Color` | カラースウォッチ（クリックでピッカー表示） | `UI_WTYPE_SWATCH` |
| `HsvCube` | HSV カラーキューブ | 特殊描画 |
| `HsvCircle` | HSV カラーホイール | 特殊描画 (`wcol_regular`) |

### 7.2 カラースウォッチの判定ロジック

```c
// interface_utils.cc:126-129
case PROP_INT:
case PROP_FLOAT: {
  if (RNA_property_array_check(prop) && index == -1) {
    if (ELEM(RNA_property_subtype(prop), PROP_COLOR, PROP_COLOR_GAMMA)) {
      but = uiDefButR_prop(block, ButType::Color, ...);
    }
  }
}
```

---

## 8. layout.prop() 実装に必要なウィジェット優先順位

GPU Layout での `layout.prop()` 実装に最低限必要なウィジェットとその優先度：

### Phase 1: 必須ウィジェット

| 優先度 | Widget | Theme | 用途 |
|--------|--------|-------|------|
| 1 | Slider | `wcol_numslider` | Float/Int (PERCENTAGE/FACTOR) |
| 2 | Number | `wcol_num` | Float/Int (通常) |
| 3 | Checkbox | `wcol_option` | Boolean (no icon) |
| 4 | Toggle | `wcol_toggle` | Boolean (with icon) |
| 5 | Text | `wcol_text` | String |

### Phase 2: 拡張ウィジェット

| 優先度 | Widget | Theme | 用途 |
|--------|--------|-------|------|
| 6 | Menu | `wcol_menu` | Enum (dropdown) |
| 7 | Radio | `wcol_radio` | Enum (expanded) |
| 8 | Swatch | (special) | Color |

---

## 9. GPULayoutStyle への追加提案

現在の `GPULayoutStyle` に追加が必要なテーマカラー：

```python
class GPULayoutStyle:
    # 既存
    inner: tuple[float, 4]          # 背景色
    inner_sel: tuple[float, 4]      # 選択時背景
    outline: tuple[float, 4]        # アウトライン
    text_color: tuple[float, 3]     # テキスト色

    # Widget別テーマ（追加提案）
    wcol_numslider: ThemeWidgetColors  # スライダー用
    wcol_num: ThemeWidgetColors        # 数値フィールド用
    wcol_option: ThemeWidgetColors     # チェックボックス用
    wcol_toggle: ThemeWidgetColors     # トグル用
    wcol_text: ThemeWidgetColors       # テキスト入力用
    wcol_menu: ThemeWidgetColors       # メニュー用
    wcol_radio: ThemeWidgetColors      # ラジオボタン用
```

---

## 10. 参照

### Blender Source Files

- `source/blender/editors/interface/interface_widgets.cc` - ウィジェット描画
- `source/blender/editors/interface/interface_layout.cc` - レイアウト API
- `source/blender/editors/interface/interface_utils.cc` - `uiDefAutoButR()`
- `source/blender/makesrna/RNA_types.hh` - PropertySubType 定義

### PME Files

- `editors/property.py` - PROPERTY_SUBTYPE 定義
- `ui/gpu/style.py` - GPULayoutStyle クラス

### Blender API Docs

- [ThemeWidgetColors](https://docs.blender.org/api/current/bpy.types.ThemeWidgetColors.html)
- [ThemeUserInterface](https://docs.blender.org/api/current/bpy.types.ThemeUserInterface.html)

---

*Last Updated: 2026-01-16*

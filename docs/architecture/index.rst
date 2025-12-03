.. _architecture-index:

======================================
PME Architecture Deep Dive
======================================

PME2設計のための内部理解ガイド
======================================

.. admonition:: このドキュメントの目的
   :class: tip

   Pie Menu Editor (PME) の内部アーキテクチャを「なぜこうなっているのか」という
   設計意図から解説し、PME2を再設計できるレベルの理解を得ることを目標とします。

.. toctree::
   :maxdepth: 2
   :caption: アーキテクチャドキュメント

   self
   data_model
   debugging
   extending

----

.. contents:: このページの目次
   :depth: 2
   :local:

----

概要：PMEとは何か
==================

本質的な役割
------------

PMEは単なる「パイメニューエディター」ではありません。

.. card:: PMEの本質
   :class-card: sd-border-primary

   **BlenderのUIを動的に生成・登録するフレームワーク**

   - パイメニュー、通常メニュー、ポップアップ、パネル
   - マクロオペレーター、モーダルオペレーター
   - スティッキーキー、スタックキー
   - カスタムプロパティ

   これら全てを **統一的なデータモデル** で管理し、
   **ホットキーと連動** させて動的に登録します。


PMEが解決している問題
----------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - 問題
     - PMEの解決策
   * - Blender APIでUI作成は面倒
     - GUIエディターで視覚的に作成
   * - ホットキー管理が複雑
     - メニューとホットキーを一体管理
   * - Pythonコードが必要
     - ドラッグ&ドロップでコマンド追加
   * - 設定の保存・共有が難しい
     - JSON形式でエクスポート/インポート


サポートされるメニュータイプ
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 20 65

   * - Mode
     - モジュール
     - 説明
   * - ``PMENU``
     - ``ed_pie_menu.py``
     - パイメニュー（8+2固定スロット）
   * - ``RMENU``
     - ``ed_menu.py``
     - 通常のドロップダウンメニュー
   * - ``DIALOG``
     - ``ed_popup.py``
     - ポップアップダイアログ
   * - ``SCRIPT``
     - ``ed_stack_key.py``
     - スタックキー（順次アクション）
   * - ``PANEL``
     - ``ed_panel_group.py``
     - パネルグループ
   * - ``HPANEL``
     - ``ed_hpanel_group.py``
     - 隠しパネルグループ
   * - ``STICKY``
     - ``ed_sticky_key.py``
     - スティッキーキー修飾
   * - ``MACRO``
     - ``ed_macro.py``
     - マクロオペレーター
   * - ``MODAL``
     - ``ed_modal.py``
     - モーダルオペレーター
   * - ``PROPERTY``
     - ``ed_property.py``
     - カスタムプロパティ

----

メンタルモデル
===============

「全てはメニューである」
-------------------------

PMEでは、パイメニューもスタックキーもマクロも、全て ``PMItem`` という
同じデータ構造で表現されます。これが良くも悪くもPMEの特徴です。

.. mermaid::

   graph TB
       subgraph PMEPreferences["PMEPreferences (AddonPreferences)"]
           subgraph pie_menus["pie_menus: Collection[PMItem]"]
               PM1["PMItem<br/>mode=PMENU<br/>pmis: [8+2個]"]
               PM2["PMItem<br/>mode=RMENU<br/>pmis: [可変]"]
               PM3["PMItem<br/>mode=MACRO<br/>pmis: [可変]"]
               PM4["PMItem<br/>mode=STICKY<br/>pmis: [2個]"]
           end
       end

       style PMEPreferences fill:#1a1a2e,stroke:#58a6ff
       style pie_menus fill:#21262d,stroke:#30363d


.. warning:: 設計上のトレードオフ

   この「統一モデル」は柔軟性をもたらすが、同時に複雑さも生みます。

   例：パイメニューは固定8+2スロット、通常メニューは可変。
   同じ ``PMItem`` で表現するため、エディターごとに解釈が異なります。


モード駆動型アーキテクチャ
---------------------------

PMEのアーキテクチャは「モード」を中心に設計されています：

.. code-block:: text

   ユーザーが「Pie Menu」を作成
           │
           ▼
   PMItem.mode = 'PMENU' が設定される
           │
           ▼
   PMEPreferences.ed('PMENU') でエディターを取得
           │
           ▼
   EdPieMenu インスタンスがUIと動作を決定

このパターンにより、新しいメニュータイプを追加する際は：

1. 新しい ``ed_*.py`` モジュールを作成
2. ``EditorBase`` を継承したクラスを定義
3. ``MODULES`` タプルに追加
4. 自動的に統合される

----

データモデル詳解
=================

types.py のコア構造
--------------------

PMEのデータ構造は ``types.py`` に定義されています。
3つの主要な ``PropertyGroup`` を理解することが重要です。

PMItem（メニュー定義）
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: types.py - PMItem の主要プロパティ

   class PMItem(bpy.types.PropertyGroup):
       # === 識別情報 ===
       # name は PropertyGroup から継承（Blenderコレクションのキー）

       mode: EnumProperty(items=CC.PM_ITEMS)  # PMENU, RMENU, MACRO...

       # === ホットキー設定 ===
       km_name: StringProperty(default="Window")  # キーマップ名
       key: EnumProperty(items=KH.key_items)      # A, SPACE, LEFTMOUSE...
       ctrl: BoolProperty()
       shift: BoolProperty()
       alt: BoolProperty()
       oskey: BoolProperty()
       any: BoolProperty()
       key_mod: EnumProperty()    # 修飾キー
       chord: EnumProperty()      # コードキー
       open_mode: EnumProperty()  # PRESS, CLICK, DOUBLE_CLICK...

       # === アイテムコレクション ===
       pmis: CollectionProperty(type=PMIItem)

       # === 追加設定 ===
       data: StringProperty()      # URL形式の拡張データ
       poll_cmd: StringProperty()  # 表示条件（Pythonコード）
       tag: StringProperty()       # タグ（カンマ区切り）
       enabled: BoolProperty()     # 有効/無効


PMIItem（アイテム定義）
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: types.py - PMIItem の主要プロパティ

   class PMIItem(bpy.types.PropertyGroup):
       # name は PropertyGroup から継承（表示名）

       mode: EnumProperty(items=CC.EMODE_ITEMS)  # COMMAND, PROP, MENU...
       text: StringProperty(maxlen=CC.MAX_STR_LEN)  # コマンド/パス
       icon: StringProperty()  # アイコン名 + フラグ
       enabled: BoolProperty(default=True)


PMLink（ツリービュー用）
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: types.py - PMLink

   class PMLink(bpy.types.PropertyGroup):
       pm_name: StringProperty()   # 参照するPMItem名
       is_folder: BoolProperty()   # フォルダか否か
       label: StringProperty()     # 表示ラベル
       folder: StringProperty()    # 親フォルダ
       group: StringProperty()     # グループ名


アイテムモード（EMODE_ITEMS）
------------------------------

``PMIItem.mode`` が取りうる値と、その振る舞い：

.. tabs::

   .. tab:: COMMAND

      **Pythonコード実行**

      ``text`` フィールドにPythonコードを格納。
      実行時に ``exec()`` される。

      .. code-block:: python

         # text の例
         bpy.ops.mesh.primitive_cube_add()
         bpy.ops.transform.translate('INVOKE_DEFAULT')

   .. tab:: PROP

      **プロパティウィジェット表示**

      ``text`` フィールドにプロパティパスを格納。
      UIに直接プロパティウィジェットが描画される。

      .. code-block:: python

         # text の例
         C.scene.render.engine
         C.object.location

   .. tab:: MENU

      **サブメニュー参照**

      ``text`` フィールドにPMEメニュー名を格納。
      ``@`` プレフィックスで展開表示。

      .. code-block:: python

         # text の例
         MySubMenu      # ボタンとして表示
         @MySubMenu     # 展開して表示

   .. tab:: HOTKEY

      **ホットキー実行**

      ``text`` フィールドにホットキー文字列を格納。
      そのホットキーに紐づくオペレーターを実行。

      .. code-block:: python

         # text の例
         Ctrl+Z
         Shift+D

   .. tab:: CUSTOM

      **カスタムレイアウト**

      ``text`` フィールドにレイアウトコードを格納。
      ``L`` 変数で ``UILayout`` にアクセス可能。

      .. code-block:: python

         # text の例
         L.prop(C.object, "name")
         L.operator("mesh.primitive_cube_add", text="Cube")

   .. tab:: EMPTY

      **セパレーター/空スロット**

      ``text`` で種類を指定：

      - ``""`` : セパレーター
      - ``"column"`` : 新しいカラム
      - ``"spacer"`` : スペーサー
      - ``"label"`` : ラベル


データエンコーディング
-----------------------

PMItem.data のURL形式
~~~~~~~~~~~~~~~~~~~~~~

追加設定は URL クエリパラメータ形式で ``PMItem.data`` に格納されます：

.. code-block:: text

   # パイメニューの追加設定
   pm?pm_radius=150&pm_threshold=20&pm_flick=True

   # ポップアップダイアログの設定
   pd?pd_title=True&pd_box=False&pd_width=300

   # スティッキーキーの設定
   sk?sk_block_ui=True


パース処理（pme.py）
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :caption: pme.py - ParsedData

   class ParsedData:
       def __init__(self, text):
           # "pm?pm_radius=150&pm_flick=True" を分解
           self.type, _, data = text.partition("?")  # type = "pm"

           # デフォルト値を設定
           for k, prop in props.prop_map.items():
               if prop.type == self.type:
                   setattr(self, k, prop.default)

           # クエリパラメータをパース
           for param in data.split("&"):
               if not param:
                   continue
               k, v = param.split("=")
               if k in props.prop_map:
                   setattr(self, k, props.prop_map[k].decode_value(v))

   # 使用例
   prop = pme.props.parse(pm.data)
   radius = prop.pm_radius  # 150
   flick = prop.pm_flick    # True


.. warning:: 脆弱性ポイント

   このURL形式には以下の問題があります：

   - **型安全性がない**: 全て文字列から変換
   - **スキーマが明示されていない**: ``props_map`` で管理
   - **バージョン間の互換性維持が手動**: ``compatibility_fixes.py`` で対応

----

実行パイプライン
=================

全体フロー
----------

.. mermaid::

   sequenceDiagram
       participant User as ユーザー
       participant KM as Blender Keymap
       participant OP as WM_OT_pme_user_pie_menu_call
       participant CTX as PMEContext
       participant Draw as _draw_item
       participant Exec as exec/eval

       User->>KM: ホットキーを押す
       KM->>OP: invoke() 呼び出し
       OP->>OP: pm.poll() チェック
       OP->>CTX: pm, event を設定
       OP->>Draw: popup_menu_pie() / popup_menu()

       loop 各 PMIItem
           Draw->>CTX: pmi, index を設定
           Draw->>Draw: pmi.mode に応じてUI生成
       end

       User->>OP: アイテムをクリック
       OP->>Exec: コマンド実行
       Exec->>CTX: gen_globals() で環境構築
       Exec-->>User: 結果


詳細ステップ
------------

Step 1: ホットキー登録
~~~~~~~~~~~~~~~~~~~~~~~

アドオン起動時、各 ``PMItem`` のホットキーが登録されます：

.. code-block:: python
   :caption: types.py - PMItem.register_hotkey()

   def register_hotkey(self, km_names=None):
       pr = get_prefs()

       if km_names is None:
           km_names = self.parse_keymap()

       for km_name in km_names:
           pr.kh.keymap(km_name)  # キーマップを選択
           kmi = pr.kh.operator(
               WM_OT_pme_user_pie_menu_call,
               None,
               self.key,
               self.ctrl, self.shift, self.alt, self.oskey,
               self.key_mod,
               self.any,
           )
           kmi.properties.pie_menu_name = self.name

           # 登録状態を記録
           self.kmis_map[self.name] = {km_name: kmi}


Step 2: オペレーター呼び出し
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ホットキーが押されると ``WM_OT_pme_user_pie_menu_call.invoke()`` が呼ばれます：

.. code-block:: python
   :caption: operators.py - invoke() の概要

   def invoke(self, context, event):
       pr = get_prefs()
       pm = pr.pie_menus[self.pie_menu_name]

       # Poll チェック
       if not pm.poll(self.__class__, context):
           return {'CANCELLED'}

       # PMEContext を設定
       pme.context.pm = pm
       pme.context.event = event

       # メニュータイプに応じて描画
       if pm.mode == 'PMENU':
           context.window_manager.popup_menu_pie(
               event, self._draw_pm, title=pm.name
           )
       elif pm.mode == 'RMENU':
           context.window_manager.popup_menu(
               self._draw_rm, title=pm.name
           )
       # ... 他のモード


Step 3: アイテム描画
~~~~~~~~~~~~~~~~~~~~

``_draw_item`` 静的メソッドが各アイテムを描画します：

.. code-block:: python
   :caption: operators.py - _draw_item() の概要

   @staticmethod
   def _draw_item(pr, pm, pmi, idx):
       pme.context.pmi = pmi
       pme.context.idx = idx

       if pmi.mode == 'COMMAND':
           # オペレーター呼び出しを解析
           op_bl_idname, args, pos_args = operator_utils.find_operator(pmi.text)

           if op_bl_idname and not pos_args:
               # 直接オペレーターボタンを配置
               text, icon, *_ = pmi.parse()
               p = lh.operator(op_bl_idname, text, icon)
               operator_utils.apply_properties(p, args, pm, pmi)
           else:
               # 汎用コマンド実行ボタン
               lh.operator(
                   WM_OT_pme_user_command_exec.bl_idname,
                   text, icon,
                   cmd=pmi.text,
                   menu=pm.name,
                   slot=pmi.name,
               )

       elif pmi.mode == 'PROP':
           # プロパティウィジェットを配置
           obj = eval(obj_path, pme.context.globals)
           lh.prop(obj, prop_name, text, icon)

       elif pmi.mode == 'CUSTOM':
           # カスタムコードを実行
           pme.context.layout = lh.layout
           exec_globals = pme.context.gen_globals()
           pme.context.exe(pmi.text, exec_globals)


Step 4: コマンド実行
~~~~~~~~~~~~~~~~~~~~

ユーザーがアイテムをクリックすると、対応するアクションが実行されます：

.. code-block:: python
   :caption: operators.py - WM_OT_pme_user_command_exec

   class WM_OT_pme_user_command_exec(bpy.types.Operator):
       bl_idname = "wm.pme_user_command_exec"

       cmd: StringProperty()
       menu: StringProperty()
       slot: StringProperty()

       def execute(self, context):
           pme.context.exec_operator = self
           exec_globals = pme.context.gen_globals()
           exec_globals.update(menu=self.menu, slot=self.slot)

           pme.context.exe(self.cmd, exec_globals)

           return exec_globals.get("return_value", {'FINISHED'})

----

PMEContext - 実行時コンテキスト
================================

役割と構造
----------

``pme.context`` はメニュー描画・コマンド実行時に必要な情報を保持するシングルトンです。

.. code-block:: python
   :caption: pme.py - PMEContext

   class PMEContext:
       def __init__(self):
           self._globals = dict(
               bpy=bpy,
               pme_context=self,
               drag_x=0,
               drag_y=0,
           )

           # 現在処理中のメニュー/アイテム
           self.pm = None       # 現在の PMItem
           self.pmi = None      # 現在の PMIItem
           self.index = None    # アイテムインデックス

           # UI描画時の一時情報
           self._layout = None  # UILayout (L でアクセス)
           self._event = None   # Event (E でアクセス)

           # 実行コンテキスト
           self.exec_globals = None
           self.exec_locals = None
           self.exec_user_locals = dict()


グローバル変数の提供
---------------------

``__init__.py`` の ``on_context()`` で便利なショートカットが登録されます：

.. code-block:: python
   :caption: __init__.py - グローバル変数登録

   def on_context():
       pme.context.add_global("D", bpy.data)          # D.objects['Cube']
       pme.context.add_global("T", bpy.types)         # T.Object
       pme.context.add_global("O", bpy.ops)           # O.mesh.primitive_cube_add()
       pme.context.add_global("P", bpy.props)         # P.BoolProperty()
       pme.context.add_global("sys", sys)

       # プロパティ関数のショートカット
       pme.context.add_global("BoolProperty", bpy.props.BoolProperty)
       pme.context.add_global("IntProperty", bpy.props.IntProperty)
       # ...

これにより、ユーザーコードで以下のような短縮形が使えます：

.. code-block:: python

   # ユーザーが書くコマンド例
   L.prop(C.object, "name")              # L = Layout, C = Context
   D.objects['Cube'].select_set(True)    # D = bpy.data
   O.mesh.primitive_cube_add()           # O = bpy.ops


gen_globals() メソッド
-----------------------

``exec()`` / ``eval()`` 用のグローバル辞書を生成します：

.. code-block:: python
   :caption: pme.py - gen_globals()

   def gen_globals(self, **kwargs):
       ret = dict(
           text=self.text,           # 現在のアイテムのテキスト
           icon=self.icon,           # 現在のアイテムのアイコン
           icon_value=self.icon_value,
           PME=temp_prefs(),         # セッション設定
           PREFS=get_prefs(),        # 永続設定
           **kwargs
       )

       ret.update(self.exec_user_locals)  # ユーザー定義変数
       ret.update(self.globals)           # 基本グローバル (D, T, O, etc.)

       return ret

----

エディターアーキテクチャ
=========================

EditorBase パターン
--------------------

各メニュータイプには専用の「エディター」クラスがあり、
``EditorBase`` を継承しています。

.. mermaid::

   classDiagram
       class EditorBase {
           +id: str
           +icon: str
           +default_name: str
           +has_hotkey: bool
           +supported_slot_modes: set
           +on_pm_add(pm)
           +on_pm_rename(pm, new_name)
           +on_pmi_edit(pm, pmi)
           +on_pm_enabled(pm, enabled)
           +draw_items(layout, pm)
           +init_pm(pm)
       }

       class EdPieMenu {
           +id = "PMENU"
           +on_pm_add(pm)
           +draw_items(layout, pm)
       }

       class EdMenu {
           +id = "RMENU"
           +on_pm_add(pm)
           +draw_items(layout, pm)
       }

       class EdMacro {
           +id = "MACRO"
           +on_pm_add(pm)
           +init_pm(pm)
       }

       EditorBase <|-- EdPieMenu
       EditorBase <|-- EdMenu
       EditorBase <|-- EdMacro


エディター登録の仕組み
-----------------------

各エディターモジュールの ``register()`` 関数で登録されます：

.. code-block:: python
   :caption: ed_pie_menu.py - エディター定義例

   class Editor(EditorBase):
       id = 'PMENU'
       icon = 'NONE'
       default_name = "Pie Menu"
       has_hotkey = True
       supported_slot_modes = {'COMMAND', 'PROP', 'MENU', 'HOTKEY', 'CUSTOM'}

       def on_pm_add(self, pm):
           """新規パイメニュー作成時: 10個のスロットを初期化"""
           for i in range(10):
               pm.pmis.add()

       def draw_items(self, layout, pm):
           """エディターUIにスロット配置を描画"""
           # パイメニュー独自の8方向 + 2追加スロットUI
           pass

   def register():
       Editor()  # PMEPreferences.editors に登録される


preferences.py での利用
------------------------

.. code-block:: python
   :caption: preferences.py - エディター利用

   class PMEPreferences(AddonPreferences):
       editors = {}  # mode → Editor インスタンス

       def ed(self, mode):
           """mode からエディターインスタンスを取得"""
           return self.editors.get(mode)

       def add_pm(self, mode, name=None):
           """新しいメニューを追加"""
           ed = self.ed(mode)
           pm = self.pie_menus.add()
           pm.mode = mode
           pm.name = name or ed.default_name
           ed.on_pm_add(pm)  # エディター固有の初期化
           return pm


.. tip:: 拡張性

   この設計により、新しいメニュータイプを追加する場合：

   1. ``ed_*.py`` を作成
   2. ``EditorBase`` を継承
   3. ``MODULES`` タプルに追加

   これだけで自動的に統合されます。

----

状態管理
=========

状態の種類と所在
-----------------

PMEには3種類の状態があります：

.. card:: 永続的な状態
   :class-card: sd-border-success

   **PMEPreferences** (``bpy.context.preferences.addons['pme'].prefs``)

   - ``pie_menus``: 全メニューデータ (Collection[PMItem])
   - ``editors``: エディターインスタンス (dict[mode, Editor])
   - 各種ユーザー設定

.. card:: セッション状態
   :class-card: sd-border-warning

   **WindowManager.pme** (``temp_prefs()``)

   - ``links``: ツリービュー用リンク (Collection[PMLink])
   - ``tags``: タグ一覧 (Collection[Tag])
   - ``pmi_data``: 編集中のアイテムデータ

.. card:: 実行時状態
   :class-card: sd-border-info

   **pme.context** (PMEContext singleton)

   - ``pm``, ``pmi``, ``index``: 現在処理中の対象
   - ``layout``, ``event``: Blenderコンテキスト
   - ``_globals``: exec用グローバル辞書

   **PMItem.kmis_map** (class variable)

   - ホットキー登録状態 ``{pm_name: {km_name: KeymapItem}}``


図解
----

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────────────┐
   │                         永続的な状態                                 │
   │  ┌─────────────────────────────────────────────────────────────┐   │
   │  │ PMEPreferences (bpy.context.preferences.addons['pme'].prefs) │   │
   │  │   ├─ pie_menus: Collection[PMItem]  ← 全メニューデータ       │   │
   │  │   ├─ editors: dict[mode, Editor]    ← エディターインスタンス │   │
   │  │   └─ various settings               ← ユーザー設定          │   │
   │  └─────────────────────────────────────────────────────────────┘   │
   └─────────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────────┐
   │                      セッション状態 (temp)                           │
   │  ┌─────────────────────────────────────────────────────────────┐   │
   │  │ WindowManager.pme (temp_prefs())                            │   │
   │  │   ├─ links: Collection[PMLink]      ← ツリービュー用        │   │
   │  │   ├─ tags: Collection[Tag]          ← タグ一覧              │   │
   │  │   └─ pmi_data: PMIData              ← 編集中アイテム        │   │
   │  └─────────────────────────────────────────────────────────────┘   │
   └─────────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────────┐
   │                     実行時状態 (runtime)                             │
   │  ┌─────────────────────────────────────────────────────────────┐   │
   │  │ pme.context (PMEContext singleton)                          │   │
   │  │   ├─ pm, pmi, index                 ← 現在処理中の対象      │   │
   │  │   ├─ layout, event                  ← Blenderコンテキスト   │   │
   │  │   └─ _globals                       ← exec用グローバル辞書  │   │
   │  └─────────────────────────────────────────────────────────────┘   │
   │                                                                      │
   │  ┌─────────────────────────────────────────────────────────────┐   │
   │  │ PMItem.kmis_map (class variable)                            │   │
   │  │   └─ {pm_name: {km_name: KeymapItem}}  ← ホットキー登録状態 │   │
   │  └─────────────────────────────────────────────────────────────┘   │
   └─────────────────────────────────────────────────────────────────────┘

----

ホットキー管理
===============

KeymapHelper
-------------

``keymap_helper.py`` の ``KeymapHelper`` クラスがホットキー登録を管理します：

.. code-block:: python
   :caption: keymap_helper.py - KeymapHelper の概要

   class KeymapHelper:
       def __init__(self):
           self.keymaps = []
           self.keymap = None

       def available(self):
           """キーマップが利用可能かチェック"""
           return bpy.context.window_manager.keyconfigs.addon is not None

       def keymap(self, name):
           """キーマップを選択"""
           kc = bpy.context.window_manager.keyconfigs.addon
           self.keymap = kc.keymaps.new(name=name, space_type='EMPTY')
           self.keymaps.append(self.keymap)

       def operator(self, cls, hotkey, key, ctrl, shift, alt, oskey, key_mod, any):
           """オペレーターをキーマップに登録"""
           kmi = self.keymap.keymap_items.new(
               cls.bl_idname,
               key, 'PRESS',
               ctrl=ctrl, shift=shift, alt=alt, oskey=oskey,
               key_modifier=key_mod, any=any,
           )
           return kmi


キーマップ待機問題
-------------------

.. warning:: 脆弱性ポイント

   Blender起動時、全てのキーマップがすぐに利用可能ではありません。
   PMEは ``PME_OT_wait_keymaps`` オペレーターでタイマー監視を行い、
   キーマップが利用可能になったら登録を試みます。

.. code-block:: python
   :caption: __init__.py - キーマップ待機

   class PME_OT_wait_keymaps(bpy.types.Operator):
       def modal(self, context, event):
           if event.type == 'TIMER':
               init_keymaps()  # 登録を試みる

               pr = get_prefs()
               if not pr.missing_kms or self.timer.time_duration > 5:
                   # 完了またはタイムアウト
                   self.remove_timer()
                   return {'FINISHED'}

           return {'PASS_THROUGH'}

``missing_kms`` は登録できなかったキーマップを追跡する辞書で、
後でリトライするために使用されます。

----

セッション復元
===============

問題の背景
----------

Blenderは新しいファイルを開くとき、一時的に ``AddonPreferences`` が
リセットされることがあります（特にBlender 5.0未満）。
PMEはこれに対処するため、ファイル読み込み前後にハンドラーを設定しています。

実装詳細
--------

.. code-block:: python
   :caption: __init__.py - セッション復元

   @persistent
   def load_pre_handler(_):
       """ファイル読み込み前: 設定をバックアップ"""
       global tmp_data
       if APP_VERSION < (5, 0, 0):
           tmp_data = property_utils.to_dict(get_prefs())

   @persistent
   def load_post_handler(filepath):
       """ファイル読み込み後: 必要に応じて復元"""
       global tmp_data
       if APP_VERSION < (5, 0, 0):
           if tmp_data is None:
               return
           if not bpy.data.filepath:  # 新規ファイルの場合
               property_utils.from_dict(get_prefs(), tmp_data)
           tmp_data = None


.. note:: Blender 5.0以降

   Blender 5.0以降ではプリファレンスの永続化方式が変わり、
   このハックは不要になった可能性があります。
   ただし、完全には検証されていません。

----

動的クラス生成
===============

なぜ必要か
----------

Blender APIでは ``Panel`` / ``Menu`` クラスを事前に定義する必要がありますが、
PMEはユーザーが任意の数のメニューを作れます。
この矛盾を解決するため、クラスを実行時に動的生成しています。

通常メニュー（RMENU）の例
--------------------------

.. code-block:: python
   :caption: ui_utils.py - 動的メニュークラス生成

   pme_menu_classes = {}

   def get_pme_menu_class(pm_name):
       """PMEメニュー用のMenuクラスを動的生成"""
       class_name = "PME_MT_" + re.sub(r'\W', '_', pm_name)

       if class_name in pme_menu_classes:
           return class_name

       # 動的にクラスを生成
       cls = type(
           class_name,
           (bpy.types.Menu,),
           {
               'bl_label': pm_name,
               'bl_idname': class_name,
               'draw': gen_draw_func(pm_name),
           }
       )

       bpy.utils.register_class(cls)
       pme_menu_classes[class_name] = cls
       return class_name


パネル拡張
----------

.. code-block:: python
   :caption: ed_base.py - 既存パネルへの追加

   EXTENDED_PANELS = {}

   def extend_panel(pm):
       """既存のBlenderパネルにPME描画を追加"""
       if pm.name in EXTENDED_PANELS:
           return

       tp_name, _, _ = U.extract_str_flags_b(pm.name, CC.F_RIGHT, CC.F_PRE)
       tp = getattr(bpy.types, tp_name, None)

       if tp and issubclass(tp, bpy.types.Panel):
           draw_func = gen_panel_draw(pm.name)
           tp.append(draw_func)  # 既存パネルに描画関数を追加
           EXTENDED_PANELS[pm.name] = draw_func


.. warning:: 注意点

   動的生成されたクラスは適切にアンレジストする必要があります。
   メニュー削除時やアドオン無効化時に忘れるとBlenderがクラッシュする可能性があります。

----

脆弱性ポイント一覧
===================

.. list-table::
   :header-rows: 1
   :widths: 20 35 25 20

   * - 領域
     - 脆弱性
     - 影響
     - 優先度
   * - セッション復元
     - ``to_dict/from_dict`` によるデータドリフト
     - 設定消失、データ破損
     - 高
   * - キーマップ登録
     - タイミング依存、``missing_kms`` 管理
     - ホットキー動作せず
     - 高
   * - URL形式data
     - スキーマなし、型安全性なし
     - パース失敗、デフォルト適用漏れ
     - 中
   * - 動的クラス生成
     - 名前衝突、アンレジスト漏れ
     - Blenderクラッシュ
     - 中
   * - exec/eval
     - ユーザーコードの例外処理
     - UIフリーズ、エラー表示
     - 中
   * - Poll関数
     - 動的コンパイル、キャッシュ管理
     - パフォーマンス、メモリリーク
     - 低


最も危険な箇所
---------------

.. danger:: PMItem.poll_methods

   ``poll_cmd`` をコンパイルしてキャッシュする仕組みですが、
   メニュー削除時にクリーンアップされない可能性があります。

   .. code-block:: python

      # types.py
      class PMItem:
          poll_methods = {}  # クラス変数！

          def update_poll_cmd(self, context):
              if self.poll_cmd == CC.DEFAULT_POLL:
                  self.poll_methods.pop(self.name, None)
              else:
                  co = compile(...)
                  self.poll_methods[self.name] = co

   メニューをリネームしても古いキーが残る可能性があります。

----

暗黙の設計哲学
===============

オリジナル作者から継承されたもの
---------------------------------

1. 「とにかく動かす」優先
~~~~~~~~~~~~~~~~~~~~~~~~~~

型チェックや厳密なバリデーションより、柔軟性と即時動作を優先。
``try/except`` で囲んで ``print_exc()`` するパターンが多い。

.. code-block:: python

   # 典型的なパターン
   try:
       obj = eval(path, pme.context.globals)
       lh.prop(obj, prop_name)
   except:
       print_exc(path)
       lh.error(text)


2. グローバル状態の活用
~~~~~~~~~~~~~~~~~~~~~~~~

``pme.context``, ``lh`` (LayoutHelper), クラス変数など、
グローバルにアクセス可能な状態を多用。

**利点**: 短いコードを書ける

**欠点**: テスタビリティを下げる


3. Blender APIへの密結合
~~~~~~~~~~~~~~~~~~~~~~~~~

抽象化レイヤーなしでBlender APIを直接使用。

**利点**: パフォーマンス、実装の簡潔さ

**欠点**: Blenderバージョン変更に脆弱


4. 「一つのデータ構造で全て表現」
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``PMItem``/``PMIItem`` で10種類以上の異なる概念を表現。

**利点**: データモデルがシンプル

**欠点**: 各タイプ固有の制約を表現しにくい


.. note:: これらは「悪い設計」ではない

   単独開発者が機能を素早く追加するには合理的なアプローチでした。
   ただし、チーム開発やメンテナンスフェーズでは課題になります。

----

モジュール依存関係
===================

MODULES順序の意味
------------------

``__init__.py`` の ``MODULES`` タプルはインポート順序を定義しており、
循環参照を避けるために重要です。

.. code-block:: text

   インポート順序 (依存方向は下→上)
   ═══════════════════════════════════════════════════════════════════

   [Core Layer]
   addon ─────────────────────── 基本設定、get_prefs(), temp_prefs()
      │
   pme ───────────────────────── PMEContext, props (データパーサー)
      │
   constants ─────────────────── 定数、ENUMアイテム

   [Utility Layer]
   utils, bl_utils ───────────── 汎用ユーティリティ
      │
   layout_helper ─────────────── lh シングルトン (UI構築ヘルパー)
      │
   keymap_helper ─────────────── KeymapHelper, ホットキー管理

   [Data Layer]
   types ─────────────────────── PMItem, PMIItem, Tag, PMLink
      │
   operators ─────────────────── 主要オペレーター群

   [Editor Layer]
   ed_base ───────────────────── EditorBase 基底クラス
      │
   ed_pie_menu, ed_menu, ...  ── 各エディター実装

   [UI Layer]
   preferences ───────────────── PMEPreferences, 設定UI


.. tip:: 循環参照の回避

   この順序は循環インポートを避けるために設計されています。
   例: ``operators.py`` は ``types.py`` より後なので、
   ``types.py`` で operators を import できません。

----

PME2への提言
=============

保持すべきもの
---------------

.. grid:: 2

   .. grid-item-card:: 統一データモデルのコンセプト
      :class-card: sd-border-success

      PMItem/PMIItem の「全てはメニューアイテム」という抽象化は強力。
      ただし、型レベルでの制約は追加すべき。

   .. grid-item-card:: PMEContextによるグローバル変数提供
      :class-card: sd-border-success

      ``L``, ``C``, ``D`` などの短縮形はUXとして優秀。
      ユーザーコードの簡潔さを維持すべき。

   .. grid-item-card:: EditorBaseパターン
      :class-card: sd-border-success

      各メニュータイプごとにエディターを分離する設計は良い。
      Protocol (インターフェース) として明示化するとさらに良い。

   .. grid-item-card:: JSON形式のエクスポート/インポート
      :class-card: sd-border-success

      ポータビリティの確保は重要。
      スキーマバージョン管理を追加すべき。


再設計すべきもの
-----------------

データエンコーディング
~~~~~~~~~~~~~~~~~~~~~~~

.. grid:: 2

   .. grid-item::

      **現在:**

      .. code-block:: python

         "pm?pm_radius=150&pm_flick=True"

   .. grid-item::

      **提案:**

      .. code-block:: python

         @dataclass
         class PieMenuData:
             radius: int = 150
             threshold: int = 20
             flick: bool = False


状態管理
~~~~~~~~~

グローバルシングルトンを減らし、明示的な依存性注入へ。
特に ``PMItem.kmis_map`` のようなクラス変数は危険。

セッション復元
~~~~~~~~~~~~~~~

``to_dict/from_dict`` パターンは脆弱。
Blender 5.0+ の新しいプリファレンス永続化を活用すべき。

エラーハンドリング
~~~~~~~~~~~~~~~~~~~

``try/except/print_exc()`` の乱用を減らす。
Result型やOptional型で明示的なエラー伝播を。

Poll関数のコンパイル
~~~~~~~~~~~~~~~~~~~~~

動的な ``compile()`` は避け、宣言的なコンテキスト条件システムを検討。


削除を検討すべきもの
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 項目
     - 理由
   * - ``c_utils.py``
     - Blender内部構造体へのアクセスは非常に脆弱
   * - 過度なレガシー互換性コード
     - PME2では最低サポートバージョンを上げ、クリーンスタート
   * - 複雑なセッション復元ロジック
     - Blender 5.0未満のハックは不要になる可能性が高い


抽象化すべきもの
-----------------

Blender API ラッパー
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # 現在: 直接呼び出し
   bpy.context.window_manager.keyconfigs.user.keymaps

   # 提案: 抽象化レイヤー
   class BlenderKeymapService(Protocol):
       def get_keymap(self, name: str) -> Optional[Keymap]: ...
       def register_hotkey(self, config: HotkeyConfig) -> Result[KeymapItem]: ...


宣言的UI定義
~~~~~~~~~~~~~

.. code-block:: python

   # 提案
   @menu_definition
   class MyPieMenu:
       slots = [
           Slot(icon="CUBE", command="bpy.ops.mesh.primitive_cube_add()"),
           Slot(icon="SPHERE", submenu=MySphereMenu),
           EmptySlot(),
           # ...
       ]

----

PME2 アーキテクチャ提案
========================

レイヤード設計
---------------

.. mermaid::

   graph TB
       subgraph Presentation["Presentation Layer"]
           EV[EditorViews]
           MR[MenuRenderer]
           PP[PrefsPanel]
       end

       subgraph Application["Application Layer"]
           MS[MenuService]
           KS[KeymapService]
           ES[ExportService]
       end

       subgraph Domain["Domain Layer"]
           ME[Menu Entity]
           IE[Item Entity]
           DE[Domain Events]
       end

       subgraph Infrastructure["Infrastructure Layer"]
           BPA[BlenderPrefs Adapter]
           BKA[BlenderKeymap Adapter]
           FSA[FileStorage Adapter]
       end

       Presentation --> Application
       Application --> Domain
       Application --> Infrastructure

       style Presentation fill:#2d5a27,stroke:#3fb950
       style Application fill:#1a3a5c,stroke:#58a6ff
       style Domain fill:#5c3a1a,stroke:#d29922
       style Infrastructure fill:#3a1a3a,stroke:#a371f7


利点
~~~~

- **Blender API変更の影響を局所化**: Infrastructure Layerに閉じ込められる
- **テスト可能**: Domain/Application LayerはBlenderなしでテスト可能
- **保守性**: 責務が明確


移行戦略
---------

.. mermaid::

   gantt
       title PME → PME2 移行計画
       dateFormat  YYYY-MM

       section Phase 1
       テストの追加         :p1a, 2024-01, 2M
       型アノテーション追加  :p1b, after p1a, 1M
       ドキュメント整備     :p1c, after p1a, 1M

       section Phase 2
       新データモデル定義   :p2a, after p1b, 2M
       API抽象化レイヤー    :p2b, after p2a, 2M
       データ変換ロジック   :p2c, after p2a, 1M

       section Phase 3
       パイメニュー移植     :p3a, after p2b, 2M
       通常メニュー移植     :p3b, after p3a, 1M
       その他機能移植       :p3c, after p3b, 2M

       section Phase 4
       移行ツール作成       :p4a, after p3b, 1M
       互換性レイヤー       :p4b, after p4a, 1M


.. tip:: 推奨アプローチ

   最初から全機能を再実装しようとしないでください。
   コア機能 (パイメニュー) をしっかり作り、順次拡張することをお勧めします。

----

参照ファイル一覧
=================

主要ファイルの概要
-------------------

.. list-table::
   :header-rows: 1
   :widths: 25 50 10 15

   * - ファイル
     - 主要な内容
     - 重要度
     - 行数目安
   * - ``pme.py``
     - PMEContext, PMEProps, ParsedData
     - ★★★
     - ~300
   * - ``types.py``
     - PMItem, PMIItem, PMLink, Tag
     - ★★★
     - ~900
   * - ``operators.py``
     - WM_OT_pme_user_pie_menu_call, 各種オペレーター
     - ★★★
     - ~2000
   * - ``ed_base.py``
     - EditorBase, 共通オペレーター
     - ★★☆
     - ~1500
   * - ``preferences.py``
     - PMEPreferences, Import/Export
     - ★★☆
     - ~1500
   * - ``keymap_helper.py``
     - KeymapHelper, ホットキー管理
     - ★★☆
     - ~500
   * - ``layout_helper.py``
     - LayoutHelper (lh), UI構築ヘルパー
     - ★☆☆
     - ~600
   * - ``__init__.py``
     - モジュール読み込み順、セッション復元
     - ★☆☆
     - ~500


推奨する読む順序
-----------------

1. ``types.py`` - データ構造を理解
2. ``pme.py`` - 実行コンテキストを理解
3. ``operators.py`` - 実行フローを理解
4. ``ed_base.py`` - エディターパターンを理解
5. 任意の ``ed_*.py`` - 具体的なエディター実装

----

まとめ
=======

キーポイント
-------------

.. grid:: 2

   .. grid-item-card:: データ構造
      :class-card: sd-border-info

      - ``PMItem`` = メニュー定義
      - ``PMIItem`` = アイテム定義
      - ``mode`` で振る舞いを決定
      - URL形式のdata拡張

   .. grid-item-card:: 実行フロー
      :class-card: sd-border-info

      - Keymap → Operator → Draw → Exec
      - ``pme.context`` で状態共有
      - 動的クラス生成でUI登録

   .. grid-item-card:: 設計パターン
      :class-card: sd-border-warning

      - EditorBase継承パターン
      - グローバルシングルトン多用
      - try/except防御的プログラミング

   .. grid-item-card:: 脆弱性
      :class-card: sd-border-danger

      - セッション復元
      - キーマップタイミング
      - 型安全性の欠如


最終メッセージ
---------------

.. admonition:: PME2に向けて
   :class: tip

   PMEは「動くことが正義」の時代に作られた素晴らしいツールです。

   PME2ではその精神を継承しつつ、モダンな設計原則を取り入れることで、
   **より保守しやすく、拡張しやすく、テストしやすい** コードベースを目指しましょう。

----

.. rubric:: 関連ドキュメント

- :ref:`CLAUDE.md <claude-md>` - 開発者向けガイドライン
- :ref:`User Documentation <user-docs>` - ユーザー向けドキュメント

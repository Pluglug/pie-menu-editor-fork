.. _extending:

======================================
エディター拡張ガイド
======================================

新しいメニュータイプを追加する方法を解説します。
この知識はPME2の設計にも役立ちます。

----

エディター追加の基本手順
=========================

1. 新しいモジュールの作成
--------------------------

``ed_example.py`` を作成：

.. code-block:: python
   :caption: ed_example.py

   import bpy
   from .ed_base import EditorBase
   from .addon import get_prefs
   from . import constants as CC

   class Editor(EditorBase):
       # === 必須属性 ===
       id = 'EXAMPLE'           # ユニークなID
       icon = 'QUESTION'        # Blenderアイコン名
       default_name = "Example Menu"

       # === オプション属性 ===
       has_hotkey = True        # ホットキー登録するか
       supported_slot_modes = {'COMMAND', 'PROP', 'MENU', 'CUSTOM'}

       # === 必須メソッド ===
       def on_pm_add(self, pm):
           """新規作成時の初期化"""
           # 例: 3つの空スロットを作成
           for i in range(3):
               pm.pmis.add()

       # === オプションメソッド ===
       def on_pm_rename(self, pm, new_name):
           """リネーム時の処理"""
           old_name = pm.name
           pm.name = new_name
           # 必要に応じて追加処理

       def on_pmi_edit(self, pm, pmi):
           """アイテム編集後の処理"""
           pass

       def on_pm_enabled(self, pm, enabled):
           """有効/無効切り替え時の処理"""
           if enabled:
               pm.register_hotkey()
           else:
               pm.unregister_hotkey()

       def init_pm(self, pm):
           """メニュー登録時の処理（起動時に呼ばれる）"""
           if pm.enabled:
               pm.register_hotkey()

       def draw_items(self, layout, pm):
           """エディターUIの描画"""
           for i, pmi in enumerate(pm.pmis):
               row = layout.row()
               row.prop(pmi, "name")
               row.prop(pmi, "text")


   def register():
       Editor()  # エディターを登録


   def unregister():
       pass  # 必要に応じてクリーンアップ


2. MODULES への追加
--------------------

``__init__.py`` の ``MODULES`` タプルに追加：

.. code-block:: python
   :caption: __init__.py

   MODULES = (
       # ... 既存のモジュール ...
       "ed_example",   # ← 追加（ed_base より後）
       "preferences",
   )


3. 定数の追加
--------------

``constants.py`` に新しいモードを追加：

.. code-block:: python
   :caption: constants.py

   # PM_ITEMS に追加
   PM_ITEMS = [
       # ... 既存の項目 ...
       ('EXAMPLE', "Example", "Example menu type", 'QUESTION', 99),
   ]

   # ED_DATA に追加（エディター選択メニュー用）
   ED_DATA = [
       # ... 既存の項目 ...
       ('EXAMPLE', "Example Menu", 'QUESTION'),
   ]

----

実際のエディター実装例
=======================

パイメニューエディター（ed_pie_menu.py）
-----------------------------------------

パイメニューは固定8+2スロットという特殊な構造を持ちます：

.. code-block:: python

   class Editor(EditorBase):
       id = 'PMENU'
       icon = 'NONE'
       default_name = "Pie Menu"
       has_hotkey = True
       supported_slot_modes = {'COMMAND', 'PROP', 'MENU', 'HOTKEY', 'CUSTOM'}

       def on_pm_add(self, pm):
           """パイメニューは常に10スロット"""
           for i in range(10):
               pm.pmis.add()

       def draw_items(self, layout, pm):
           """8方向 + 2追加の独自レイアウト"""
           # 上段: N (slot 2)
           row = layout.row()
           row.scale_y = 1.5
           self.draw_slot(row, pm, 2, 'N')

           # 中段: W (4), 中央, E (0)
           row = layout.row()
           self.draw_slot(row, pm, 4, 'W')
           row.separator()
           self.draw_slot(row, pm, 0, 'E')

           # 下段: S (6)
           row = layout.row()
           row.scale_y = 1.5
           self.draw_slot(row, pm, 6, 'S')

           # 追加スロット (8, 9)
           box = layout.box()
           self.draw_slot(box, pm, 8, 'Extra 1')
           self.draw_slot(box, pm, 9, 'Extra 2')


マクロエディター（ed_macro.py）
-------------------------------

マクロは Blender の Macro オペレーターを動的生成します：

.. code-block:: python

   class Editor(EditorBase):
       id = 'MACRO'
       icon = 'POSE_DATA'
       default_name = "Macro"
       has_hotkey = True
       docs = "#macro-operator"

       default_pmi_data = "COMMAND"
       supported_slot_modes = {'COMMAND', 'MENU'}

       def on_pm_add(self, pm):
           """初期アイテムなし（ユーザーが追加）"""
           pass

       def on_pmi_edit(self, pm, pmi):
           """アイテム変更時にマクロを再構築"""
           from .macro_utils import update_macro
           update_macro(pm)

       def init_pm(self, pm):
           """起動時にマクロオペレーターを登録"""
           from .macro_utils import add_macro
           add_macro(pm)
           if pm.enabled:
               pm.register_hotkey()


モーダルエディター（ed_modal.py）
---------------------------------

モーダルオペレーターは複数のコールバックモードを持ちます：

.. code-block:: python

   class Editor(EditorBase):
       id = 'MODAL'
       icon = 'LONGDISPLAY'
       default_name = "Modal"
       has_hotkey = True

       # モーダル固有のアイテムモード
       supported_slot_modes = {
           'COMMAND', 'PROP',
           'INVOKE',   # 起動時
           'FINISH',   # 完了時
           'CANCEL',   # キャンセル時
           'UPDATE',   # 更新時
       }

       def on_pm_add(self, pm):
           """コールバック用の初期アイテム"""
           # INVOKE
           pmi = pm.pmis.add()
           pmi.mode = 'INVOKE'
           pmi.name = 'On Invoke'

           # 中間アイテム用のスペース
           pm.pmis.add()

           # FINISH
           pmi = pm.pmis.add()
           pmi.mode = 'FINISH'
           pmi.name = 'On Finish'

----

エディターUIのカスタマイズ
===========================

draw_items メソッド
--------------------

``draw_items`` はエディターパネルのUI描画を担当します：

.. code-block:: python

   def draw_items(self, layout, pm):
       """
       Args:
           layout: bpy.types.UILayout
           pm: PMItem インスタンス
       """
       # LayoutHelper を使用
       from .layout_helper import lh

       lh.lt(layout)

       for i, pmi in enumerate(pm.pmis):
           # アイテム行
           row = lh.row()

           # インデックス
           lh.label(str(i))

           # 名前
           row.prop(pmi, "name", text="")

           # モード
           row.prop(pmi, "mode", text="")

           # コマンド/テキスト
           row.prop(pmi, "text", text="")

           # 有効/無効
           row.prop(pmi, "enabled", text="", icon='CHECKBOX_HLT')


共通オペレーターの使用
-----------------------

``ed_base.py`` には共通で使えるオペレーターが定義されています：

.. code-block:: python

   from .ed_base import (
       PME_OT_pm_add,           # メニュー追加
       PME_OT_pm_edit,          # メニュー編集
       WM_OT_pmi_data_edit,     # アイテムデータ編集
       WM_OT_pmi_icon_select,   # アイコン選択
   )

   def draw_items(self, layout, pm):
       # アイテム追加ボタン
       layout.operator(
           "wm.pmi_add",
           text="Add Item",
           icon='ADD'
       )

       # アイコン選択ボタン
       for i, pmi in enumerate(pm.pmis):
           row = layout.row()
           row.operator(
               WM_OT_pmi_icon_select.bl_idname,
               text="",
               icon=pmi.icon or 'NONE'
           ).pm_item = i

----

データ拡張
===========

PMItem.data への新しいプロパティ追加
-------------------------------------

1. ``pme.py`` でプロパティを定義：

.. code-block:: python
   :caption: pme.py

   # PMEProps クラス内、または register() で
   props.StringProperty('ex', 'ex_custom', '')      # 文字列
   props.BoolProperty('ex', 'ex_enabled', True)     # 真偽値
   props.IntProperty('ex', 'ex_count', 0)           # 整数

   # 'ex' は type プレフィックス（URL の最初の部分）


2. ``types.py`` でアクセサを定義：

.. code-block:: python
   :caption: types.py - PMItem 内

   # computed property として定義
   ex_custom: bpy.props.StringProperty(
       get=lambda s: s.get_data("ex_custom"),
       set=lambda s, v: s.set_data("ex_custom", v),
   )

   ex_enabled: bpy.props.BoolProperty(
       get=lambda s: s.get_data("ex_enabled"),
       set=lambda s, v: s.set_data("ex_enabled", v),
   )


3. エディターUIで使用：

.. code-block:: python

   def draw_extra(self, layout, pm):
       box = layout.box()
       box.label(text="Example Settings")
       box.prop(pm, "ex_custom")
       box.prop(pm, "ex_enabled")

----

実行ロジックのカスタマイズ
===========================

カスタムオペレーターの作成
---------------------------

メニュータイプ固有のオペレーターが必要な場合：

.. code-block:: python

   class PME_OT_example_action(bpy.types.Operator):
       bl_idname = "pme.example_action"
       bl_label = "Example Action"
       bl_options = {'INTERNAL'}

       pm_name: bpy.props.StringProperty()

       def execute(self, context):
           pr = get_prefs()
           pm = pr.pie_menus.get(self.pm_name)
           if not pm:
               return {'CANCELLED'}

           # カスタムロジック
           for pmi in pm.pmis:
               if pmi.mode == 'COMMAND':
                   pme.context.exe(pmi.text)

           return {'FINISHED'}


WM_OT_pme_user_pie_menu_call との統合
--------------------------------------

メニュー呼び出し時の処理をカスタマイズする場合、
``operators.py`` の ``WM_OT_pme_user_pie_menu_call.invoke()`` を確認：

.. code-block:: python

   def invoke(self, context, event):
       pr = get_prefs()
       pm = pr.pie_menus[self.pie_menu_name]

       # モードに応じて分岐
       if pm.mode == 'PMENU':
           # パイメニュー
           context.window_manager.popup_menu_pie(event, self._draw_pm)

       elif pm.mode == 'RMENU':
           # 通常メニュー
           context.window_manager.popup_menu(self._draw_rm)

       elif pm.mode == 'EXAMPLE':  # ← 新しいモードを追加
           # カスタム処理
           self.execute_example(pm)

       # ...

----

テストの追加
=============

新しいエディターのテスト
-------------------------

.. code-block:: python
   :caption: tests/test_ed_example.py

   import bpy
   import pytest

   @pytest.fixture
   def pme_prefs():
       return bpy.context.preferences.addons['pie_menu_editor'].preferences

   class TestExampleEditor:
       def test_create_menu(self, pme_prefs):
           """メニュー作成テスト"""
           pm = pme_prefs.add_pm('EXAMPLE', 'Test Example')

           assert pm.name == 'Test Example'
           assert pm.mode == 'EXAMPLE'
           assert len(pm.pmis) == 3  # on_pm_add で3つ作成

       def test_add_item(self, pme_prefs):
           """アイテム追加テスト"""
           pm = pme_prefs.pie_menus['Test Example']
           pm.pmis[0].mode = 'COMMAND'
           pm.pmis[0].text = 'print("test")'

           assert pm.pmis[0].mode == 'COMMAND'

       def test_hotkey_registration(self, pme_prefs):
           """ホットキー登録テスト"""
           pm = pme_prefs.pie_menus['Test Example']
           pm.key = 'E'
           pm.ctrl = True
           pm.register_hotkey()

           assert pm.name in pm.kmis_map

----

ベストプラクティス
===================

.. admonition:: 推奨事項
   :class: tip

   1. **EditorBase のメソッドを適切にオーバーライドする**

      必要なメソッドだけオーバーライドし、不要な場合は親クラスの実装を使う

   2. **PMEContext を正しく使用する**

      .. code-block:: python

         # Good
         exec_globals = pme.context.gen_globals()
         pme.context.exe(cmd, exec_globals)

         # Bad
         exec(cmd, {'bpy': bpy})  # グローバル変数が不足

   3. **エラーハンドリングを適切に行う**

      .. code-block:: python

         try:
             result = some_operation()
         except Exception:
             from .addon import print_exc
             print_exc()
             return {'CANCELLED'}

   4. **UI更新を忘れずに**

      .. code-block:: python

         # データ変更後
         from .ui import tag_redraw
         tag_redraw()

         # ツリー更新が必要な場合
         pr.update_tree()


.. admonition:: 避けるべきこと
   :class: warning

   1. **クラス変数への依存を最小限に**

      特に ``poll_methods``, ``kmis_map`` のようなパターンは避ける

   2. **循環インポートに注意**

      エディターモジュールは ``operators.py`` より後に読み込まれるため、
      ``operators.py`` をインポートする際は関数内で行う

   3. **Blender API の直接使用を最小限に**

      将来の抽象化のため、可能な限りPMEのユーティリティを使用

----

PME2への示唆
=============

現在のエディターシステムから学べること：

良い点
-------

- プラグイン的な拡張性（``MODULES`` に追加するだけ）
- 共通インターフェース（``EditorBase``）
- メソッドのオーバーライドによるカスタマイズ

改善すべき点
-------------

- 型安全性の欠如（Protocol/ABC を使うべき）
- クラス変数による状態管理（インスタンス管理が望ましい）
- テストの不足

.. code-block:: python
   :caption: PME2での推奨パターン

   from typing import Protocol
   from dataclasses import dataclass

   class EditorProtocol(Protocol):
       id: str
       icon: str

       def on_pm_add(self, pm: "Menu") -> None: ...
       def on_pm_rename(self, pm: "Menu", new_name: str) -> None: ...
       def draw_items(self, layout: "UILayout", pm: "Menu") -> None: ...

   @dataclass
   class EditorConfig:
       id: str
       icon: str
       default_name: str
       has_hotkey: bool = True
       supported_slot_modes: frozenset[str] = frozenset()

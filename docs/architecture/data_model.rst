.. _data-model:

======================================
データモデル詳解
======================================

このページでは、PMEのデータモデルをより詳細に解説します。

----

PropertyGroup の継承階層
=========================

.. mermaid::

   classDiagram
       class bpy_struct {
           <<Blender Internal>>
       }

       class PropertyGroup {
           <<bpy.types>>
           +name: str
           +keys()
           +values()
           +items()
       }

       class PMItem {
           +mode: EnumProperty
           +km_name: StringProperty
           +key: EnumProperty
           +pmis: CollectionProperty
           +data: StringProperty
           +poll_cmd: StringProperty
       }

       class PMIItem {
           +mode: EnumProperty
           +text: StringProperty
           +icon: StringProperty
           +enabled: BoolProperty
       }

       class PMLink {
           +pm_name: StringProperty
           +is_folder: BoolProperty
           +label: StringProperty
       }

       class Tag {
           +filtered_pms: ClassVar
       }

       bpy_struct <|-- PropertyGroup
       PropertyGroup <|-- PMItem
       PropertyGroup <|-- PMIItem
       PropertyGroup <|-- PMLink
       PropertyGroup <|-- Tag

----

PMItem の全プロパティ
======================

識別情報
---------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - プロパティ
     - 型
     - 説明
   * - ``name``
     - str
     - メニュー名（PropertyGroupから継承、コレクションキー）
   * - ``mode``
     - Enum
     - メニュータイプ（PMENU, RMENU, MACRO 等）
   * - ``label``
     - str (computed)
     - getter/setterによるリネーム処理付きプロパティ


ホットキー設定
---------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - プロパティ
     - 型
     - 説明
   * - ``km_name``
     - str
     - キーマップ名（複数はセミコロン区切り）
   * - ``key``
     - Enum
     - キー（A, SPACE, LEFTMOUSE 等）
   * - ``ctrl``
     - bool
     - Ctrlキー
   * - ``shift``
     - bool
     - Shiftキー
   * - ``alt``
     - bool
     - Altキー
   * - ``oskey``
     - bool
     - OS/Cmdキー
   * - ``any``
     - bool
     - 任意の修飾キー
   * - ``key_mod``
     - Enum
     - 追加の修飾キー
   * - ``chord``
     - Enum
     - コードキー（Chordsモード用）
   * - ``open_mode``
     - Enum
     - 起動モード（PRESS, CLICK, DOUBLE_CLICK, CLICK_DRAG, CHORDS）
   * - ``drag_dir``
     - Enum
     - ドラッグ方向（CLICK_DRAGモード用）


アイテムコレクション
---------------------

.. code-block:: python

   pmis: CollectionProperty(type=PMIItem)

- パイメニュー: 常に10個（8方向 + 2追加）
- 通常メニュー: 可変長
- スタックキー: 可変長
- スティッキーキー: 2個（押下時、解放時）


追加設定（data）
-----------------

``data`` プロパティはURL形式で追加設定を格納します：

.. code-block:: python

   # パイメニュー固有の設定
   pm_radius: int     # 半径（-1 = デフォルト）
   pm_threshold: int  # 選択しきい値
   pm_confirm: int    # 確定距離
   pm_flick: bool     # リリースで確定

   # ポップアップダイアログ固有
   pd_title: bool     # タイトル表示
   pd_box: bool       # フレーム使用
   pd_auto_close: bool  # マウスアウトで閉じる
   pd_width: int      # 幅

   # 通常メニュー固有
   rm_title: bool     # タイトル表示

   # スティッキーキー固有
   sk_block_ui: bool  # UI ブロック

   # モーダル固有
   confirm: bool      # リリースで確定
   block_ui: bool     # UI ブロック
   lock: bool         # マウスロック


Poll設定
---------

.. code-block:: python

   poll_cmd: StringProperty(default=CC.DEFAULT_POLL)

表示条件をPythonコードで指定。デフォルトは ``" return True"``。

.. warning:: 動的コンパイル

   ``poll_cmd`` は実行時に ``compile()`` されて ``poll_methods`` クラス変数にキャッシュされます。

   .. code-block:: python

      # poll_cmd の例
      " return C.mode == 'OBJECT'"
      " return C.active_object and C.active_object.type == 'MESH'"


タグ
-----

.. code-block:: python

   tag: StringProperty()

カンマ区切りでタグを格納：

.. code-block:: python

   # 例
   "Modeling, Transform"
   "Animation"
   ""  # タグなし


有効/無効
----------

.. code-block:: python

   enabled: BoolProperty(default=True)

``False`` の場合、ホットキーは登録されず、ツリービューでグレーアウト表示。

----

PMIItem の全プロパティ
=======================

基本情報
---------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - プロパティ
     - 型
     - 説明
   * - ``name``
     - str
     - 表示ラベル
   * - ``mode``
     - Enum
     - アイテムタイプ
   * - ``text``
     - str
     - コマンド/パス/参照名
   * - ``icon``
     - str
     - アイコン名 + フラグ
   * - ``enabled``
     - bool
     - 有効/無効


mode の詳細
------------

.. code-block:: python

   EMODE_ITEMS = [
       ('COMMAND', "Command", "", 0),      # Pythonコード
       ('PROP', "Property", "", 1),        # プロパティウィジェット
       ('MENU', "Menu", "", 2),            # サブメニュー参照
       ('HOTKEY', "Hotkey", "", 3),        # ホットキー実行
       ('CUSTOM', "Custom", "", 4),        # カスタムレイアウト
       ('EMPTY', "Empty", "", 5),          # 空/セパレーター

       # モーダル専用
       ('INVOKE', "Invoke", "", 6),        # 起動時
       ('FINISH', "Finish", "", 7),        # 完了時
       ('CANCEL', "Cancel", "", 8),        # キャンセル時
       ('UPDATE', "Update", "", 9),        # 更新時
   ]


icon のフラグ文字
------------------

``icon`` フィールドにはアイコン名の前にフラグ文字を付けられます：

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - フラグ
     - 定数
     - 説明
   * - ``#``
     - ``F_ICON_ONLY``
     - アイコンのみ表示（テキスト非表示）
   * - ``!``
     - ``F_HIDDEN``
     - 隠し表示（見えないがスペースは確保）
   * - ``^``
     - ``F_CB``
     - チェックボックススタイル（PROP用）
   * - ``&``
     - ``F_CUSTOM_ICON``
     - カスタムアイコンファイル参照

.. code-block:: python

   # 例
   "#CUBE"       # アイコンのみ
   "!NONE"       # 隠し
   "^CHECKBOX"   # チェックボックス
   "&myicon"     # カスタムアイコン


text の解釈
------------

``mode`` によって ``text`` の解釈が異なります：

.. tabs::

   .. tab:: COMMAND

      Pythonコード。セミコロンで複数文を区切り可能。

      .. code-block:: python

         "bpy.ops.mesh.primitive_cube_add()"
         "bpy.ops.transform.translate('INVOKE_DEFAULT')"
         "C.object.location.x += 1; C.object.location.y += 1"

   .. tab:: PROP

      プロパティパス。最後のドット以降がプロパティ名。

      .. code-block:: python

         "C.scene.render.engine"
         "C.object.location"
         "C.object['custom_prop']"

   .. tab:: MENU

      PMEメニュー名または Blender Menu クラス名。

      .. code-block:: python

         "MyPieMenu"         # PMEメニュー参照
         "@MyPieMenu"        # 展開表示
         "VIEW3D_MT_mesh_add"  # Blenderメニュー

   .. tab:: HOTKEY

      ホットキー文字列。

      .. code-block:: python

         "Ctrl+Z"
         "Shift+D"
         "Alt+G"

   .. tab:: CUSTOM

      レイアウトコード。``L`` で UILayout にアクセス。

      .. code-block:: python

         "L.prop(C.object, 'name')"
         "L.operator('mesh.primitive_cube_add', text='Add Cube')"

   .. tab:: EMPTY

      種類を指定する文字列。

      .. code-block:: python

         ""           # セパレーター
         "column"     # 新しいカラム開始
         "spacer"     # スペーサー
         "label"      # ラベル（name を表示）

----

PMLink の構造
==============

ツリービュー表示のためのリンク構造です。

.. code-block:: python

   class PMLink(bpy.types.PropertyGroup):
       pm_name: StringProperty()    # 参照するPMItem名
       is_folder: BoolProperty()    # フォルダか否か
       label: StringProperty()      # 表示ラベル
       folder: StringProperty()     # 親フォルダ名
       group: StringProperty()      # グループ名（キーマップ名等）

       # クラス変数
       idx = 0              # リンク生成カウンター
       paths = {}           # リンクID → パスリストのマップ


パス構造
---------

ツリービューでの階層パスは ``paths`` クラス変数で管理：

.. code-block:: python

   # 例: "Window" キーマップの "Folder1/MyMenu"
   link.name = "123"  # リンクID
   link.pm_name = "MyMenu"
   link.group = "Window"
   PMLink.paths["123"] = ["Folder1"]  # パスリスト


フルパス取得
-------------

.. code-block:: python

   def fullpath(self):
       """フルパスを取得"""
       ret = self.group + CC.TREE_SPLITTER        # "Window/"
       ret += CC.TREE_SPLITTER.join(self.path)    # "Folder1"
       if self.is_folder:
           if self.path:
               ret += CC.TREE_SPLITTER
           ret += self.pm_name
       return ret  # "Window/Folder1/MyMenu" or "Window/Folder1"

----

Tag の構造
===========

タグはフィルタリングに使用されます。

.. code-block:: python

   class Tag(bpy.types.PropertyGroup):
       # name は PropertyGroup から継承

       # クラス変数
       filtered_pms = None  # Set[str] or None


フィルタリング処理
-------------------

.. code-block:: python

   @staticmethod
   def filter():
       """現在のタグフィルターを適用"""
       pr = get_prefs()
       tpr = temp_prefs()

       if not tpr.tags or not pr.tag_filter:
           Tag.filtered_pms = None  # フィルターなし
           return

       Tag.filtered_pms = set()
       for pm in pr.pie_menus:
           if pm.has_tag(pr.tag_filter):
               Tag.filtered_pms.add(pm.name)

   @staticmethod
   def check_pm(pm):
       """PMがフィルターを通過するかチェック"""
       return Tag.filtered_pms is None or pm.name in Tag.filtered_pms

----

クラス変数の問題点
===================

PMEでは多くのクラス変数が使用されていますが、これは問題を引き起こす可能性があります。

問題のあるクラス変数一覧
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - クラス
     - 変数
     - 問題
   * - ``PMItem``
     - ``poll_methods``
     - リネーム/削除時にクリーンアップされない
   * - ``PMItem``
     - ``kmis_map``
     - 同上
   * - ``PMItem``
     - ``_prev_key_mod_map``
     - 同上
   * - ``PMLink``
     - ``idx``, ``paths``
     - ツリー再構築時のみクリア
   * - ``Tag``
     - ``filtered_pms``
     - フィルター変更時のみ更新
   * - ``PMIItem``
     - ``expandable_props``
     - 無限に成長する可能性


推奨される改善
---------------

.. code-block:: python

   # 改善案: インスタンスごとの管理
   class MenuRegistry:
       def __init__(self):
           self.poll_methods: dict[str, CodeType] = {}
           self.keymap_items: dict[str, dict[str, KeymapItem]] = {}

       def register_poll(self, pm_name: str, code: str) -> None:
           ...

       def unregister_poll(self, pm_name: str) -> None:
           ...

       def cleanup(self, pm_name: str) -> None:
           """メニュー削除時に呼ぶ"""
           self.poll_methods.pop(pm_name, None)
           self.keymap_items.pop(pm_name, None)

----

シリアライゼーション
=====================

to_dict / from_dict
--------------------

``property_utils.py`` で定義されている、プリファレンスのシリアライゼーション：

.. code-block:: python

   def to_dict(data, skip_default=True):
       """PropertyGroup を辞書に変換"""
       result = {}

       for key in data.keys():
           value = data[key]

           if isinstance(value, bpy.types.PropertyGroup):
               result[key] = to_dict(value, skip_default)
           elif hasattr(value, '__iter__') and not isinstance(value, str):
               # Collection
               result[key] = [to_dict(item, skip_default) for item in value]
           else:
               if not skip_default or value != get_default(data, key):
                   result[key] = to_py_value(value)

       return result

   def from_dict(data, values):
       """辞書から PropertyGroup を復元"""
       for key, value in values.items():
           if isinstance(value, dict):
               from_dict(getattr(data, key), value)
           elif isinstance(value, list):
               collection = getattr(data, key)
               collection.clear()
               for item_values in value:
                   item = collection.add()
                   from_dict(item, item_values)
           else:
               setattr(data, key, value)


.. warning:: データドリフト

   ``to_dict/from_dict`` は完全な往復変換を保証しません。
   特に以下のケースで問題が発生します：

   - デフォルト値がバージョン間で変わった場合
   - 新しいプロパティが追加された場合
   - プロパティの型が変わった場合

----

バージョン互換性
=================

compatibility_fixes.py
-----------------------

バージョンアップ時のデータ移行は ``compatibility_fixes.py`` で処理されます：

.. code-block:: python

   def fix(pms=None, version=None):
       """メインの修正エントリーポイント"""
       pr = get_prefs()

       if version is None:
           version = pr.version

       # バージョンごとの修正を適用
       if version < (1, 15, 0):
           fix_1_15_0(pms or pr.pie_menus)

       if version < (1, 16, 0):
           fix_1_16_0(pms or pr.pie_menus)

       # 現在のバージョンを記録
       pr.version = addon.VERSION


JSON インポート時の修正
------------------------

.. code-block:: python

   def fix_json(pm, data, version):
       """JSONインポート時のデータ修正"""

       if version < (1, 14, 0):
           # 古い形式からの変換
           ...

       if version < (1, 15, 0):
           # poll_cmd のフォーマット変更
           if len(data) > 7 and data[7]:
               pm.poll_cmd = data[7]


新しい修正関数の追加方法
-------------------------

.. code-block:: python

   def fix_X_Y_Z(pms):
       """バージョン X.Y.Z への移行修正"""
       for pm in pms:
           # 修正処理
           ...

   # fix() 関数内に追加
   if version < (X, Y, Z):
       fix_X_Y_Z(pms or pr.pie_menus)

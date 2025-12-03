.. _debugging:

======================================
デバッグガイド
======================================

PMEの開発・デバッグ時に役立つ情報をまとめています。

----

デバッグフラグ
===============

debug_utils.py
---------------

``debug_utils.py`` でデバッグフラグを制御できます：

.. code-block:: python
   :caption: debug_utils.py

   # 各フラグを True にすると対応するログが出力される
   DBG_INIT = False    # 初期化ログ
   DBG_LAYOUT = False  # UIレイアウトデバッグ
   DBG_TREE = False    # ツリービューデバッグ
   DBG_STICKY = False  # スティッキーキーデバッグ
   DBG_MACRO = False   # マクロデバッグ
   DBG_MODAL = False   # モーダルデバッグ


ログ関数
---------

.. code-block:: python

   from .debug_utils import *

   logi("情報メッセージ")     # 青色
   logw("警告メッセージ")     # 黄色
   loge("エラーメッセージ")   # 赤色
   logh("ヘッダー")          # 緑色（区切り線付き）


使用例
-------

.. code-block:: python

   if DBG_INIT:
       logh("PME Register")
       logi("Loading modules...")

   if DBG_TREE:
       logw(f"Tree update: {len(links)} links")

----

セーフモード
=============

PMEはセーフモードで起動できます。これによりメニュー登録をスキップし、
問題のあるメニューによるクラッシュを回避できます。

起動方法
---------

.. code-block:: bash

   blender --pme-safe-mode

または ``addon.py`` の ``SAFE_MODE`` を直接変更：

.. code-block:: python

   SAFE_MODE = True  # 常にセーフモードで起動


セーフモード時の動作
---------------------

- ホットキー登録がスキップされる
- 動的クラス生成がスキップされる
- エディターUIは通常通り動作
- メニューの編集・エクスポートは可能

----

よくある問題と解決策
=====================

ホットキーが動作しない
-----------------------

**症状**: メニューを作成したが、ホットキーを押しても反応しない

**チェックポイント**:

1. ``PMItem.enabled`` が ``True`` か？
2. ``PMItem.key`` が 'NONE' でないか？
3. キーマップ名が正しいか？（``PMItem.km_name``）
4. ``missing_kms`` にエントリがないか？

**デバッグ方法**:

.. code-block:: python

   # コンソールで実行
   import bpy
   pr = bpy.context.preferences.addons['pie_menu_editor'].preferences

   pm = pr.pie_menus['YourMenuName']
   print(f"enabled: {pm.enabled}")
   print(f"key: {pm.key}")
   print(f"km_name: {pm.km_name}")
   print(f"kmis_map: {pm.kmis_map.get(pm.name)}")

   # 登録されていないキーマップを確認
   print(f"missing_kms: {pr.missing_kms}")


メニューが表示されない
-----------------------

**症状**: ホットキーを押すと反応はあるが、メニューが表示されない

**チェックポイント**:

1. ``poll_cmd`` が ``True`` を返すか？
2. アイテムが空でないか？
3. エラーがコンソールに出ていないか？

**デバッグ方法**:

.. code-block:: python

   # poll の確認
   pm = pr.pie_menus['YourMenuName']
   print(f"poll_cmd: {pm.poll_cmd}")

   # poll を手動実行
   result = pm.poll(None, bpy.context)
   print(f"poll result: {result}")


コマンドが実行されない
-----------------------

**症状**: メニューは表示されるが、アイテムをクリックしても何も起きない

**チェックポイント**:

1. コマンドにシンタックスエラーがないか？
2. コンソールにエラーが出ていないか？
3. ``exec()`` のコンテキストに必要な変数があるか？

**デバッグ方法**:

.. code-block:: python

   # コマンドを手動実行
   from pie_menu_editor import pme

   cmd = "bpy.ops.mesh.primitive_cube_add()"
   exec_globals = pme.context.gen_globals()
   exec(cmd, exec_globals)


UIが更新されない
-----------------

**症状**: 設定を変更しても、UIに反映されない

**解決策**:

.. code-block:: python

   from pie_menu_editor.ui import tag_redraw
   tag_redraw()  # 全エリアを再描画

   # または特定のエリアのみ
   for area in bpy.context.screen.areas:
       area.tag_redraw()

----

内部状態の確認
===============

PMEPreferences の確認
----------------------

.. code-block:: python

   import bpy
   pr = bpy.context.preferences.addons['pie_menu_editor'].preferences

   # 全メニュー一覧
   for pm in pr.pie_menus:
       print(f"{pm.name}: mode={pm.mode}, key={pm.key}, enabled={pm.enabled}")

   # 特定のメニューの詳細
   pm = pr.pie_menus['MyMenu']
   print(f"km_name: {pm.km_name}")
   print(f"data: {pm.data}")
   print(f"poll_cmd: {pm.poll_cmd}")

   # アイテム一覧
   for i, pmi in enumerate(pm.pmis):
       print(f"  [{i}] {pmi.name}: mode={pmi.mode}, text={pmi.text[:50]}...")


temp_prefs の確認
------------------

.. code-block:: python

   from pie_menu_editor.addon import temp_prefs
   tpr = temp_prefs()

   # タグ一覧
   print("Tags:", [t.name for t in tpr.tags])

   # ツリーリンク
   print(f"Links: {len(tpr.links)}")
   for link in tpr.links[:10]:  # 最初の10個
       print(f"  {link.pm_name}: folder={link.is_folder}")


PMEContext の確認
------------------

.. code-block:: python

   from pie_menu_editor import pme

   # 現在のコンテキスト
   print(f"pm: {pme.context.pm}")
   print(f"pmi: {pme.context.pmi}")
   print(f"index: {pme.context.index}")

   # グローバル変数
   for k, v in sorted(pme.context.globals.items()):
       print(f"  {k}: {type(v).__name__}")


エディター情報の確認
---------------------

.. code-block:: python

   pr = bpy.context.preferences.addons['pie_menu_editor'].preferences

   # 登録されているエディター
   for mode, ed in pr.editors.items():
       print(f"{mode}: {ed.__class__.__name__}")
       print(f"  icon: {ed.icon}")
       print(f"  default_name: {ed.default_name}")
       print(f"  has_hotkey: {ed.has_hotkey}")
       print(f"  supported_slot_modes: {ed.supported_slot_modes}")

----

クラス変数のクリーンアップ
===========================

問題が発生した場合、クラス変数を手動でクリアすることで解決できることがあります。

.. code-block:: python

   from pie_menu_editor.types import PMItem, PMIItem, PMLink, Tag

   # ホットキー登録マップをクリア
   PMItem.kmis_map.clear()

   # Poll メソッドキャッシュをクリア
   PMItem.poll_methods.clear()

   # 前回のkey_modマップをクリア
   PMItem._prev_key_mod_map.clear()

   # ツリーリンクをクリア
   PMLink.idx = 0
   PMLink.paths.clear()

   # タグフィルターをクリア
   Tag.filtered_pms = None

   # 拡張可能プロパティキャッシュをクリア
   PMIItem.expandable_props.clear()


.. warning:: 副作用

   クラス変数をクリアすると、一時的に機能が正しく動作しなくなる可能性があります。
   通常はBlenderを再起動するのが安全です。

----

ホットリロード
===============

開発中にモジュールをリロードする場合：

.. code-block:: python

   import importlib
   import pie_menu_editor

   # 特定のモジュールをリロード
   from pie_menu_editor import pme
   importlib.reload(pme)

   # または全モジュールをリロード（危険）
   for mod_name in pie_menu_editor.MODULES:
       mod = importlib.import_module(f"pie_menu_editor.{mod_name}")
       importlib.reload(mod)


.. danger:: 注意

   ホットリロードは状態の不整合を引き起こす可能性があります。
   特に以下の場合は避けてください：

   - ``types.py`` のリロード（PropertyGroupが変わるとクラッシュ）
   - 登録済みオペレーターのリロード

   基本的にはBlenderを再起動することを推奨します。

----

パフォーマンス計測
===================

描画時間の計測
---------------

.. code-block:: python

   import time
   from pie_menu_editor.layout_helper import lh

   class TimedLayoutHelper:
       def __init__(self, original):
           self._original = original
           self._times = {}

       def __getattr__(self, name):
           attr = getattr(self._original, name)
           if callable(attr):
               def timed(*args, **kwargs):
                   start = time.perf_counter()
                   result = attr(*args, **kwargs)
                   elapsed = time.perf_counter() - start
                   self._times[name] = self._times.get(name, 0) + elapsed
                   return result
               return timed
           return attr

       def report(self):
           for name, total in sorted(self._times.items(), key=lambda x: -x[1]):
               print(f"{name}: {total*1000:.2f}ms")


exec/eval の計測
-----------------

.. code-block:: python

   import time
   from pie_menu_editor import pme

   original_exe = pme.context.exe

   def timed_exe(data, globals=None, *args, **kwargs):
       start = time.perf_counter()
       result = original_exe(data, globals, *args, **kwargs)
       elapsed = time.perf_counter() - start
       if elapsed > 0.01:  # 10ms以上
           print(f"Slow exec ({elapsed*1000:.2f}ms): {data[:50]}...")
       return result

   pme.context.exe = timed_exe

----

テスト用ユーティリティ
=======================

テスト用メニューの作成
-----------------------

.. code-block:: python

   import bpy
   pr = bpy.context.preferences.addons['pie_menu_editor'].preferences

   # テスト用パイメニューを作成
   pm = pr.add_pm('PMENU', 'Test Pie Menu')
   pm.key = 'A'
   pm.ctrl = True

   # アイテムを追加
   pm.pmis[0].mode = 'COMMAND'
   pm.pmis[0].name = 'Add Cube'
   pm.pmis[0].text = 'bpy.ops.mesh.primitive_cube_add()'
   pm.pmis[0].icon = 'MESH_CUBE'

   # ホットキーを登録
   pm.register_hotkey()

   # UIを更新
   pr.update_tree()


テスト用メニューの削除
-----------------------

.. code-block:: python

   pm = pr.pie_menus.get('Test Pie Menu')
   if pm:
       pr.remove_pm(pm)
       pr.update_tree()


全メニューのエクスポート（デバッグ用）
---------------------------------------

.. code-block:: python

   import json
   from pie_menu_editor import property_utils

   pr = bpy.context.preferences.addons['pie_menu_editor'].preferences
   data = property_utils.to_dict(pr)

   with open('/tmp/pme_debug.json', 'w') as f:
       json.dump(data, f, indent=2)

   print(f"Exported to /tmp/pme_debug.json")

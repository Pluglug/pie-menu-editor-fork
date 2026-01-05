.. _pme-api:

===============
PME API リファレンス
===============

このドキュメントは、PME の公開 API を説明します。

.. contents::
   :local:
   :depth: 2

----

-----------
公開 API
-----------

PME 2.0 以降、``import pme`` で安定した公開 API にアクセスできます。

.. code-block:: python

    import pme

    # コード実行
    result = pme.execute("print(C.mode)")

    # メニュー操作
    pm = pme.find_pm("My Pie Menu")
    if pm:
        pme.invoke_pm(pm)

    # ユーザープロパティ
    pme.props.MyCounter = 10

    # 設定
    pme.preferences.debug_mode = True

    # カスタム関数登録
    pme.context.add_global("my_func", my_func)

    # 開発者ユーティリティ
    pme.dev.is_public("C")  # True


API 一覧
**********

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - **API**
      - **説明**
    * - ``pme.execute()``
      - Python コードを実行
    * - ``pme.evaluate()``
      - Python 式を評価
    * - ``pme.find_pm()``
      - メニューを検索
    * - ``pme.list_pms()``
      - メニュー一覧を取得
    * - ``pme.invoke_pm()``
      - メニューを呼び出し
    * - ``pme.props``
      - ユーザープロパティへのアクセス
    * - ``pme.preferences``
      - PME 設定へのアクセス
    * - ``pme.context``
      - 実行コンテキスト（``add_global()`` 用）
    * - ``pme.dev``
      - 開発者ユーティリティ（サブモジュール）


実行 API
**********

.. py:function:: pme.execute(code, *, extra_globals=None)

    任意の Python コードを PME の標準名前空間で実行します。

    :param str code: 実行する Python コード（複数行可）
    :param dict extra_globals: 追加のグローバル変数（オプション）
    :return: 実行結果を含む :class:`ExecuteResult`
    :rtype: ExecuteResult

    **例**::

        result = pme.execute("print(C.mode)")
        if not result.success:
            print(f"Error: {result.error_message}")

        # 追加変数を渡す
        result = pme.execute(
            "print(gizmo.name)",
            extra_globals={"gizmo": my_gizmo}
        )

    .. note::
        実行時に利用可能な標準変数: ``C``, ``D``, ``bpy``, ``E``, ``L``, ``U``, ``delta``, ``drag_x``, ``drag_y`` など


.. py:function:: pme.evaluate(expr, *, extra_globals=None)

    式を評価して結果を返します。

    :param str expr: 評価する Python 式
    :param dict extra_globals: 追加のグローバル変数（オプション）
    :return: 式の評価結果
    :raises: 構文エラーや未定義変数の場合は例外を送出

    **例**::

        mode = pme.evaluate("C.mode")
        is_edit = pme.evaluate("C.mode == 'EDIT_MESH'")

    .. warning::
        ``execute()`` と異なり、失敗時は例外を送出します。
        フォールバックが必要な場合は try-except で囲んでください。


.. py:class:: pme.ExecuteResult

    実行結果を表すデータクラス。

    .. py:attribute:: success
        :type: bool

        実行が成功したかどうか

    .. py:attribute:: error_message
        :type: str | None

        失敗時のエラーメッセージ


メニュー API
*************

.. py:function:: pme.find_pm(name)

    名前でパイメニューを検索します。

    :param str name: メニューの正確な名前
    :return: 見つかった場合は :class:`PMHandle`、それ以外は ``None``

    **例**::

        pm = pme.find_pm("My Pie Menu")
        if pm:
            print(f"Found: {pm.name} ({pm.mode})")


.. py:function:: pme.list_pms(mode=None)

    すべてのパイメニューを列挙します。

    :param str mode: メニュータイプでフィルタ（``'PMENU'``, ``'RMENU'``, ``'DIALOG'`` など）
    :return: :class:`PMHandle` のリスト

    **例**::

        all_menus = pme.list_pms()
        pie_menus = pme.list_pms(mode='PMENU')


.. py:function:: pme.invoke_pm(pm_or_name)

    パイメニューを呼び出し（表示）します。

    :param pm_or_name: :class:`PMHandle` またはメニュー名
    :type pm_or_name: PMHandle | str
    :return: 成功した場合は ``True``

    **例**::

        pme.invoke_pm("My Pie Menu")

        # または
        pm = pme.find_pm("My Pie Menu")
        if pm:
            pme.invoke_pm(pm)


.. py:class:: pme.PMHandle

    パイメニューへのハンドル。

    .. py:attribute:: name
        :type: str

        メニュー名

    .. py:attribute:: mode
        :type: str | None

        メニュータイプ（``'PMENU'``, ``'RMENU'``, ``'DIALOG'`` など）

    .. py:attribute:: enabled
        :type: bool

        メニューが有効かどうか


ユーザープロパティ
********************

.. py:data:: pme.props

    Property Editor で定義したユーザープロパティへのアクセス。

    ``bpy.context.preferences.addons['pie_menu_editor'].preferences.props`` と同じオブジェクトを返します。

    **例**::

        # 値の取得
        value = pme.props.MyCounter

        # 値の設定
        pme.props.MyCounter = 10

    .. note::
        スクリプト名前空間内では ``props()`` 関数も利用可能です。
        詳細は :ref:`スクリプト名前空間 <scripting-namespace>` を参照。


設定
******

.. py:data:: pme.preferences

    PME アドオン設定へのアクセス。

    ``bpy.context.preferences.addons['pie_menu_editor'].preferences`` と同じオブジェクトを返します。

    **例**::

        prefs = pme.preferences
        prefs.debug_mode = True


コンテキスト
*************

.. py:data:: pme.context

    PME の実行コンテキスト。カスタム関数の登録に使用します。

    .. py:method:: add_global(key, value)

        グローバル名前空間にカスタム関数または値を登録します。

        :param str key: アクセス名
        :param value: 登録する関数または値

        **例**::

            def my_tool():
                bpy.ops.mesh.select_all(action='TOGGLE')

            pme.context.add_global("toggle_select", my_tool)

            # スクリプト内で使用可能に:
            # toggle_select()

    .. py:attribute:: globals
        :type: dict

        グローバル名前空間辞書へのアクセス。

    .. note::
        コード実行には ``pme.execute()`` / ``pme.evaluate()`` の使用を推奨します。


----

.. _pme-dev-api:

-----------
開発者 API
-----------

``pme.dev`` サブモジュールは、外部ツール開発者や PME コントリビューター向けのユーティリティを提供します。

.. code-block:: python

    import pme

    # 変数が公開かどうか確認
    pme.dev.is_public("C")      # True
    pme.dev.is_public("PME")    # False

    # 安定性レベルを取得
    pme.dev.get_stability("C")  # Stability.EXPERIMENTAL

    # 名前空間レポート
    print(pme.dev.namespace_report())


内省関数
**********

.. py:function:: pme.dev.is_public(name)

    変数名が公開 API かどうかを判定します。

    :param str name: 変数名
    :return: 公開なら ``True``
    :rtype: bool


.. py:function:: pme.dev.is_internal(name)

    変数名が内部用かどうかを判定します。

    :param str name: 変数名
    :return: 内部用なら ``True``
    :rtype: bool


.. py:function:: pme.dev.get_stability(name)

    変数名の安定性レベルを取得します。

    :param str name: 変数名
    :return: 安定性レベル
    :rtype: Stability


.. py:function:: pme.dev.get_public_names_by_stability(stability)

    指定した安定性レベルの公開変数名一覧を取得します。

    :param Stability stability: 安定性レベル
    :return: 変数名のリスト
    :rtype: list[str]


.. py:class:: pme.dev.Stability

    安定性レベルの列挙型。

    .. py:attribute:: EXPERIMENTAL

        暫定仕様。変更の可能性あり。

    .. py:attribute:: STABLE

        安定仕様。互換性を維持。


デバッグユーティリティ
************************

.. py:function:: pme.dev.validate_namespace(globals_dict=None)

    名前空間の設定を検証します。

    :param dict globals_dict: 検証対象（省略時は現在のコンテキスト）
    :return: ``{'missing': [...], 'warnings': [...]}``
    :rtype: dict


.. py:function:: pme.dev.namespace_report()

    名前空間の状態をレポートします。

    :return: 人間可読なレポート文字列
    :rtype: str

    **例**::

        >>> print(pme.dev.namespace_report())
        === PME Namespace Report ===

        Public (Experimental):
          ✓ C: Blender context
          ✓ D: Blender data
          ...


定数
******

.. py:data:: pme.dev.PUBLIC_NAMES

    公開変数名のセット。


----

.. _scripting-namespace:

-------------------
スクリプト名前空間
-------------------

PME のスロットエディタ（コマンドタブ、カスタムタブ）内で利用できる変数と関数です。

グローバル変数
*****************

Core（Blender API ショートカット）
====================================

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - **変数**
      - **説明**
    * - ``C``
      - `bpy.context <https://docs.blender.org/api/current/bpy.context.html>`_ へのアクセス
    * - ``D``
      - `bpy.data <https://docs.blender.org/api/current/bpy.data.html>`_ へのアクセス
    * - ``bpy``
      - Blender Python モジュール

イベント情報
================

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - **変数**
      - **説明**
    * - ``E``
      - 現在の `Event <https://docs.blender.org/api/current/bpy.types.Event.html>`_ オブジェクト
    * - ``delta``
      - マウスホイールのデルタ値（``1``, ``-1``, ``0``）
    * - ``drag_x``, ``drag_y``
      - ドラッグ移動量（ピクセル）

UI コンテキスト
=================

.. list-table::
    :header-rows: 1
    :widths: 15 85

    * - **変数**
      - **説明**
    * - ``L``
      - 現在の `UILayout <https://docs.blender.org/api/current/bpy.types.UILayout.html>`_
    * - ``text``
      - 現在のアイテムの表示テキスト
    * - ``icon``
      - 現在のアイテムのアイコン名
    * - ``icon_value``
      - 現在のアイテムのアイコン値（整数）


ユーザーデータ
================

.. py:data:: U

    セッション内で持続するユーザーデータストレージ。

    **使用例**::

        # 値の設定
        U.my_counter = 0
        U.update(foo="value1", bar="value2")

        # 値の取得
        value = U.my_counter
        value = U.get("my_counter", 0)  # デフォルト値付き

    .. note::
        Blender を再起動するとデータは失われます。


グローバル関数
*****************

メニュー操作
=================

.. py:function:: open_menu(name, slot=None, **kwargs)

    名前でメニューを開きます。

    :param str name: メニュー名
    :param slot: スロットのインデックスまたは名前（スタックキー用）
    :type slot: int | str | None
    :param kwargs: モーダル/マクロオペレーターに渡す引数
    :return: メニューが存在する場合は ``True``

    **例**::

        # 条件に応じてメニューを開く
        open_menu("Lamp Menu" if C.active_object.type == 'LAMP' else "Object Menu")

        # スタックキーのスロット指定
        open_menu("My Stack Key", "Ctrl slot" if E.ctrl else "Default slot")


.. py:function:: draw_menu(name, frame=False, dx=0, dy=0, layout=None)

    別のポップアップダイアログ内にメニューを描画します。

    :param str name: メニュー（ポップアップダイアログ）の名前
    :param bool frame: フレームで囲むかどうか
    :param int dx: 水平オフセット
    :param int dy: 垂直オフセット
    :param layout: カスタムレイアウト（オプション）
    :return: メニューが存在する場合は ``True``


.. py:function:: toggle_menu(name, value=None)

    メニューを有効/無効にします。

    :param str name: メニュー名
    :param bool value: ``True`` で有効、``False`` で無効、``None`` でトグル
    :return: メニューが存在する場合は ``True``


スクリプト実行
=================

.. py:function:: execute_script(path, **kwargs)

    外部 Python スクリプトを実行します。

    :param str path: スクリプトファイルパス（相対パスは ``pie_menu_editor`` フォルダから）
    :param kwargs: スクリプトに渡すキーワード引数
    :return: スクリプト内の ``return_value`` または ``True``

    **スクリプト内で利用可能な変数**: ``kwargs``, ``__file__``, ``return_value``, PME のすべてのグローバル変数

    **例**::

        # 基本的な実行
        execute_script("scripts/hello_world.py", msg="Hello!")

        # 戻り値の取得
        result = execute_script("scripts/get_data.py")

    .. warning::
        信頼できるソースのスクリプトのみ実行してください。


プロパティ操作
=================

.. py:function:: props(name=None, value=None)

    PME ユーザープロパティの値を取得または設定します。

    :param str name: プロパティ名（``None`` でコンテナを返す）
    :param value: 設定する値
    :return: コンテナ、プロパティ値、または ``True``

    **例**::

        # 値の取得
        value = props("MyProperty")
        value = props().MyProperty

        # 値の設定
        props("MyProperty", new_value)
        props().MyProperty = new_value

    .. note::
        公開 API からは ``pme.props`` でもアクセス可能です。


UI ヘルパー
=============

.. py:function:: message_box(text, icon='INFO', title="Pie Menu Editor")

    メッセージボックスを表示します。

    :param str text: 表示するメッセージ（``\n`` で改行）
    :param str icon: アイコン名（``'INFO'``, ``'ERROR'``, ``'QUESTION'`` など）
    :param str title: ウィンドウタイトル
    :return: ``True``

    **例**::

        message_box("処理が完了しました", icon='INFO')
        message_box("エラーが発生しました\n詳細を確認してください", icon='ERROR')


.. py:function:: overlay(text, **kwargs)

    オーバーレイメッセージを描画します。

    :param str text: 表示するメッセージ
    :param kwargs:
        - ``alignment``: ``'TOP'``, ``'TOP_LEFT'``, ``'TOP_RIGHT'``, ``'BOTTOM'``, ``'BOTTOM_LEFT'``, ``'BOTTOM_RIGHT'``
        - ``duration``: 表示時間（秒、デフォルト ``2.0``）
        - ``offset_x``, ``offset_y``: オフセット（ピクセル）
    :return: ``True``

    **例**::

        overlay("Hello PME!", duration=1.0, offset_y=100)


.. py:function:: input_box(func=None, prop=None)

    入力ボックスを表示します。

    :param func: 入力値で呼び出すコールバック関数
    :param str prop: 編集するプロパティパス
    :return: ``True``

    **例**::

        # プロパティを直接編集
        input_box(prop="C.active_object.name")

        # コールバックで処理
        input_box(func=lambda value: overlay(f"入力: {value}"))


.. py:function:: close_popups()

    すべてのポップアップダイアログを閉じます。

    :return: ``True``


.. py:function:: tag_redraw(area=None, region=None)

    UI エリアを再描画します。

    :param str area: 再描画する Area タイプ（``None`` で全エリア）
    :param str region: 再描画する Region タイプ（``None`` で全リージョン）
    :return: ``True``


カスタムタブ専用
==================

.. py:function:: panel(pt, frame=True, header=True, expand=None, poll=True, layout=None)

    パネルを描画します。

    :param pt: パネルクラスまたはクラス名
    :type pt: type | str
    :param bool frame: フレームで囲むかどうか
    :param bool header: ヘッダーを表示するかどうか
    :param expand: 展開状態（``True``/``False``/``None`` で前回の状態）
    :type expand: bool | None
    :param bool poll: poll メソッドを実行するかどうか
    :param layout: カスタムレイアウト
    :return: ``True``

    **例**::

        panel("MATERIAL_PT_context_material", True, True, True)


.. py:function:: operator(layout, operator, text="", icon='NONE', emboss=True, icon_value=0, **kwargs)

    プロパティ付きでオペレーターボタンを描画します。

    :param layout: UILayout インスタンス
    :param str operator: オペレーター識別子
    :param str text: ボタンテキスト
    :param str icon: アイコン名
    :param kwargs: オペレータープロパティ
    :return: OperatorProperties オブジェクト

    **例**::

        operator(L, "wm.context_set_int", "Material Slot 1",
                data_path="active_object.active_material_index", value=0)


.. py:function:: custom_icon(filename)

    カスタムアイコンの整数値を取得します。

    :param str filename: ``pie_menu_editor/icons/`` 内の拡張子なしファイル名
    :return: アイコン値（整数）

    **例**::

        L.label(text="Custom Icon", icon_value=custom_icon("my_icon"))


----

-------------------
UserData 拡張（計画中）
-------------------

現在の ``U`` は単純で使いやすいですが、大規模なスクリプトでは管理が難しくなります。
以下の拡張を検討中です。

名前付きインスタンス
**********************

.. code-block:: python

    # 将来の API 案
    my_data = pme.create_user_data("my_addon")
    my_data.counter = 0

    # グローバル U は従来通り
    U.temp = "global"

レジストリ
***********

.. code-block:: python

    # 将来の API 案
    # 登録されたインスタンスを確認
    for name, data in pme.user_data_registry.items():
        print(f"{name}: {data.__dict__}")


----

------------------
コンテキスト管理
------------------

.. py:class:: pme.context

    PME の実行コンテキスト。内部使用が主ですが、カスタム関数の登録に使用できます。

    .. py:method:: add_global(key, value)

        グローバル名前空間にカスタム関数または値を登録します。

        :param str key: アクセス名
        :param value: 登録する関数または値

        **例**::

            def my_tool():
                bpy.ops.mesh.select_all(action='TOGGLE')

            pme.context.add_global("toggle_select", my_tool)

    .. py:attribute:: globals
        :type: dict

        グローバル名前空間辞書へのアクセス。

    .. note::
        ``pme.context`` への直接アクセスは非推奨です。
        新規コードは ``pme.execute()`` / ``pme.evaluate()`` を使用してください。

    pme.contextの改善案

    # 現在
    pme.context.add_global("func", func)
    pme.context.globals["C"]

    # 将来案 A: pme.globals
    pme.globals.add("func", func)
    pme.globals["C"]

    # 将来案 B: pme.namespace
    pme.namespace.add("func", func)
    pme.namespace.get("C")

    pme.context に見えている内部属性：

    | 公開候補     | 内部のまま                   |
    |--------------|------------------------------|
    | add_global() | pm, pmi, index               |
    | globals      | exec_globals, exec_locals    |
    |              | layout, event, region        |
    |              | is_first_draw, last_operator |


----

----------
安定性レベル
----------

.. list-table::
    :header-rows: 1
    :widths: 20 80

    * - **レベル**
      - **説明**
    * - Experimental
      - v2.0.0 時点の暫定仕様。変更の可能性あり。
    * - Internal
      - 外部からの利用は非推奨。予告なく変更される可能性あり。

v2.0.0 では、すべての公開 API は **Experimental** です。
v2.1.0 以降で、利用実績を見て **Stable** に昇格するものを決定します。


----

----------
参照
----------

- :ref:`pme-scripting` — スクリプティングの基本
- `Blender Python API <https://docs.blender.org/api/current/>`_

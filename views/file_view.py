from __future__ import annotations

from typing import List, Dict
import datetime as dt

from nicegui import ui

from controllers.file_controller import (
    list_export_files,
    read_file_content,
    delete_files_between,
    delete_all_files,
)


def _fmt_dt(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S")


def _show_file_detail_dialog(row: Dict):
    path = row.get("path")
    if not path:
        ui.notify("无法获取文件路径", type="negative")
        return
    try:
        content = read_file_content(path)
    except Exception as ex:  # noqa: BLE001
        ui.notify(f"读取文件失败: {ex}", type="negative")
        return

    with ui.dialog() as dlg, ui.card().classes("w-2/3 h-2/3"):
        ui.label(row["name"]).classes("text-h6 mb-2")
        ui.textarea(
            value=content,
        ).classes("w-full h-full")

        with ui.row().classes("justify-end gap-2 mt-2"):
            ui.button("关闭", on_click=dlg.close)
    dlg.open()


def show_file_page():
    """导出文件管理界面。"""
    ui.page_title("导出文件管理")

    with ui.row().classes("items-center justify-between px-4 py-2"):
        ui.label("导出文件管理").classes("text-h6")

        with ui.row().classes("items-center gap-2"):

            def on_refresh():
                ui.navigate.reload()

            ui.button("刷新", on_click=on_refresh)

            def on_clear_all():
                def do_clear():
                    count = delete_all_files()
                    ui.notify(f"已删除 {count} 个文件", type="positive")
                    ui.navigate.reload()

                with ui.dialog() as dlg, ui.card():
                    ui.label("确认清理所有导出文件？").classes("mb-2")
                    with ui.row().classes("justify-end gap-2"):
                        ui.button("取消", on_click=dlg.close)
                        ui.button("确认", on_click=lambda: (dlg.close(), do_clear()))
                dlg.open()

            ui.button("一键清理全部", on_click=on_clear_all).props("color=negative")

    files: List[Dict] = list_export_files()

    # 时间段清理控件
    with ui.row().classes("items-center gap-2 px-4 pb-2"):
        ui.label("按时间段清理：").classes("text-sm text-grey-7")

        start_input = ui.input(label="开始时间 (YYYY-MM-DD HH:MM:SS)").classes("w-64")
        end_input = ui.input(label="结束时间 (YYYY-MM-DD HH:MM:SS)").classes("w-64")

        def on_clear_range():
            try:
                start = dt.datetime.strptime(
                    start_input.value.strip(), "%Y-%m-%d %H:%M:%S"
                )
                end = dt.datetime.strptime(end_input.value.strip(), "%Y-%m-%d %H:%M:%S")
            except Exception:  # noqa: BLE001
                ui.notify("时间格式错误，请使用 YYYY-MM-DD HH:MM:SS", type="negative")
                return

            if end < start:
                ui.notify("结束时间必须晚于开始时间", type="negative")
                return

            count = delete_files_between(start, end)
            ui.notify(f"已删除 {count} 个文件", type="positive")
            ui.navigate.reload()

        ui.button("清理该时间段文件", on_click=on_clear_range)

    with ui.column().classes("p-4 gap-3 w-full"):
        if not files:
            ui.label("当前没有导出文件").classes("text-grey-6")
            return

        rows = [
            {
                "name": f["name"],
                "size": f["size"],
                "mtime": _fmt_dt(f["mtime"]),
                "path": f["path"],
            }
            for f in files
        ]

        columns = [
            {"name": "name", "label": "文件名", "field": "name"},
            {"name": "size", "label": "大小(字节)", "field": "size"},
            {"name": "mtime", "label": "最后修改时间", "field": "mtime"},
            {"name": "action", "label": "操作", "field": "action", "align": "center"},
        ]

        table = ui.table(
            columns=columns,
            rows=rows,
            row_key="name",
        ).classes("w-full")

        table.add_slot(
            "body-cell-action",
            """
            <q-td :props="props">
                <q-btn
                    label="查看"
                    flat
                    dense
                    @click="() => $parent.$emit('detail', props.row)"
                />
            </q-td>
            """,
        )

        table.on("detail", lambda e: _show_file_detail_dialog(e.args))

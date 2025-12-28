from __future__ import annotations

from typing import List, Dict
import datetime as dt
import re  # 新增：用于提取链接

from nicegui import ui

from controllers.file_controller import (
    list_export_files,
    read_file_content,
    delete_files_between,
    delete_all_files,
    read_csv_table,  # 新增：读取 CSV 为表格
)


def _fmt_dt(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S")


def _show_file_text_dialog(row: Dict):
    """查看 CSV，仅显示链接，每行一条"""
    path = row.get("path")
    if not path:
        ui.notify("无法获取文件路径", type="negative")
        return
    try:
        data = read_csv_table(path)
    except Exception as ex:  # noqa: BLE001
        ui.notify(f"读取 CSV 失败: {ex}", type="negative")
        return

    headers: List[str] = data.get("headers") or []
    rows: List[Dict[str, str]] = data.get("rows") or []

    # 优先选择中文“链接”列，其次英文“link”，否则尝试在各字段中匹配URL
    link_key = None
    if "链接" in headers:
        link_key = "链接"
    elif "link" in headers:
        link_key = "link"

    url_pattern = re.compile(r"https?://\S+")
    links: List[str] = []
    for r in rows:
        val = (r.get(link_key) if link_key else None) or ""
        if val:
            links.append(str(val).strip())
            continue
        # 回退：尝试在各字段中寻找 URL
        found = False
        for v in r.values():
            if not v:
                continue
            m = url_pattern.search(str(v))
            if m:
                links.append(m.group(0))
                found = True
                break
        if not found:
            # 无链接则跳过该行
            continue

    content = "\n".join(links)

    with ui.dialog() as dlg, ui.card().classes("w-2/3 h-2/3"):
        ui.label(row["name"]).classes("text-h6 mb-2")
        ui.textarea(value=content).classes("w-full h-full")
        with ui.row().classes("justify-end gap-2 mt-2"):
            ui.button("关闭", on_click=dlg.close)
    dlg.open()


def _show_file_table_dialog(row: Dict):
    """以表格方式查看 CSV 内容"""
    path = row.get("path")
    if not path:
        ui.notify("无法获取文件路径", type="negative")
        return
    try:
        data = read_csv_table(path)
    except Exception as ex:  # noqa: BLE001
        ui.notify(f"读取 CSV 失败: {ex}", type="negative")
        return

    headers: List[str] = data.get("headers") or []
    rows: List[Dict[str, str]] = data.get("rows") or []
    columns = [{"name": h, "label": h, "field": h} for h in headers] or [
        {"name": "content", "label": "内容", "field": "content"}
    ]
    # 若无表头，回退为单列展示
    if not headers:
        rows = [{"content": str(r)} for r in rows]

    with ui.dialog() as dlg, ui.card().classes("w-3/4 h-3/4"):
        ui.label(row["name"]).classes("text-h6 mb-2")
        ui.table(columns=columns, rows=rows, row_key=headers[0] if headers else "content").classes("w-full")
        with ui.row().classes("justify-end gap-2 mt-2"):
            ui.button("关闭", on_click=dlg.close)
    dlg.open()


def show_file_page():
    """导出文件管理界面（仅显示 CSV）。"""
    ui.page_title("导出文件管理")

    with ui.row().classes("items-center justify-between px-4 py-2"):
        ui.label("导出文件管理（CSV）").classes("text-h6")

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
            {"name": f["name"], "size": f["size"], "mtime": _fmt_dt(f["mtime"]), "path": f["path"]}
            for f in files
        ]

        columns = [
            {"name": "name", "label": "文件名", "field": "name"},
            {"name": "size", "label": "大小(字节)", "field": "size"},
            {"name": "mtime", "label": "最后修改时间", "field": "mtime"},
            {"name": "action", "label": "操作", "field": "action", "align": "center"},
        ]

        table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")

        table.add_slot(
            "body-cell-action",
            """
            <q-td :props="props">
                <q-btn
                    label="查看文本"
                    flat
                    dense
                    class="q-mr-sm"
                    @click="() => $parent.$emit('detail_text', props.row)"
                />
                <q-btn
                    label="表格查看"
                    flat
                    dense
                    @click="() => $parent.$emit('detail_table', props.row)"
                />
            </q-td>
            """,
        )

        table.on("detail_text", lambda e: _show_file_text_dialog(e.args))
        table.on("detail_table", lambda e: _show_file_table_dialog(e.args))

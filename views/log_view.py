from __future__ import annotations

from typing import List

from nicegui import ui

from controllers.log_controller import read_log_lines, clear_log


def show_log_page():
    """日志界面：实时显示日志，并支持一键清理。"""
    ui.page_title("日志")

    with ui.row().classes("items-center justify-between px-4 py-2"):
        ui.label("日志查看").classes("text-h6")

        with ui.row().classes("items-center gap-2"):

            def on_refresh():
                ui.navigate.reload()

            ui.button("刷新", on_click=on_refresh)

            def on_clear():
                def do_clear():
                    clear_log()
                    ui.notify("日志已清空", type="positive")
                    ui.navigate.reload()

                with ui.dialog() as dlg, ui.card():
                    ui.label("确认清空日志？").classes("mb-2")
                    with ui.row().classes("justify-end gap-2"):
                        ui.button("取消", on_click=dlg.close)
                        ui.button("确认", on_click=lambda: (dlg.close(), do_clear()))

                dlg.open()

            ui.button("清空日志", on_click=on_clear).props("color=negative")

    lines: List[str] = read_log_lines(500)

    with ui.column().classes("p-4 gap-2 w-full"):
        if not lines:
            ui.label("暂无日志内容").classes("text-grey-6")
            return
        ui.textarea(
            value="\n".join(lines),
        ).classes("w-full h-[600px]")

from __future__ import annotations

from typing import Any, Dict, Callable, Optional

from nicegui import ui

from controllers.config_controller import (
    get_all_config,
    update_config_value,
    reload_config,
)


def _create_config_row(key: str, info: Dict[str, Any]):
    """渲染单行配置项。"""
    desc = info.get("desc", "")
    current_value = info.get("value", "")

    with ui.row().classes("items-center w-full gap-4"):
        ui.label(key).classes("w-40 text-bold")
        ui.label(desc).classes("grow text-grey-7 text-sm")

        value_input = ui.input(
            label="value",
            value=str(current_value),
        ).classes("w-64")

        def on_save():
            try:
                update_config_value(key, value_input.value or "")
                ui.notify(f"{key} 已保存", type="positive")
            except Exception as e:  # noqa: BLE001
                ui.notify(f"保存失败: {e}", type="negative")

        ui.button("保存", on_click=on_save).classes("ml-2")


def show_config_page(refresh: Optional[Callable[[], None]] = None):
    """配置管理主体内容（供右侧 tab 使用）。"""
    ui.page_title("配置管理")

    with ui.row().classes("items-center justify-between px-4 py-2"):
        ui.label("配置管理").classes("text-h6")
        with ui.row().classes("items-center"):

            def on_reload():
                try:
                    reload_config()
                    ui.notify("配置已从文件重新加载", type="positive")
                    if refresh is not None:
                        refresh()
                    else:
                        ui.navigate.reload()
                except Exception as e:  # noqa: BLE001
                    ui.notify(f"重新加载失败: {e}", type="negative")

            ui.button("重新加载配置", on_click=on_reload)

    with ui.column().classes("p-4 gap-3 w-full"):
        all_config = get_all_config()

        for key, info in all_config.items():
            _create_config_row(key, info)

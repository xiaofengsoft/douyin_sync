from nicegui import ui, app
from views.config_view import show_config_page
from views.order_view import show_order_page
from views.log_view import show_log_page
from views.file_view import show_file_page
from tasks.refund_task import auto_export_deficiency_orders_links


@app.on_startup
def startup_tasks():
    auto_export_deficiency_orders_links()


def main():
    @ui.page("/")
    def index():
        ui.page_title("抖音同步管理后台")  # ← 移到这里！

        with ui.row().classes("w-full h-screen no-wrap"):
            with ui.tabs().props("vertical").classes("w-40 bg-grey-2") as tabs:
                tab_config = ui.tab("配置")
                tab_orders = ui.tab("订单")
                tab_logs = ui.tab("日志")
                tab_files = ui.tab("导出文件")

            with ui.tab_panels(tabs, value=tab_config).classes("grow h-full"):
                with ui.tab_panel(tab_config):
                    show_config_page()
                with ui.tab_panel(tab_orders):
                    show_order_page()
                with ui.tab_panel(tab_logs):
                    show_log_page()
                with ui.tab_panel(tab_files):
                    show_file_page()

    ui.run(port=9991, reload=False)


if __name__ == "__main__":
    main()

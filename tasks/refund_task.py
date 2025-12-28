from typing import Any, Dict, List
import asyncio
from config import CONFIG
from controllers.order_controller import export_deficiency_orders_links
import threading
import logging
from utils.ningmeng import ningmeng

def auto_export_deficiency_orders_links():
    """
    如果配置开启自动导出功能，则自动导出数量缺失的订单链接
    """

    async def _runner():
        while True:
            if CONFIG["IS_AUTO_EXPORT"] == "1":
                deficiency_links_by_goods = await export_deficiency_orders_links()
                for goods_name in CONFIG['NINGMENG_GOODS_NAMES']:
                    links = deficiency_links_by_goods.get(goods_name, [])
                    if links:
                        result = ningmeng.refund_orders(links)
                        logging.info(f"[柠檬] 已为商品 {goods_name} 提交数量缺失订单退款申请，订单链接：{links}，返回结果：{result}")
                interval = int(CONFIG["EXPORT_TIME_INTERVAL"])  # type: ignore
            else:
                interval = 60
            await asyncio.sleep(interval)  # type: ignore

    threading.Thread(target=lambda: asyncio.run(_runner()), daemon=True).start()
    
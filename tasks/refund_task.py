from typing import Any, Dict, List
import asyncio
from config import CONFIG
from controllers.order_controller import export_deficiency_orders_links
import threading
import logging
from utils.common import play_sound
# from utils.ningmeng import ningmeng

def auto_export_deficiency_orders_links():
    """
    如果配置开启自动导出功能，则自动导出数量缺失的订单链接
    """

    async def _runner():
        while True:
            if CONFIG["IS_AUTO_EXPORT"] == "1":
                deficiency_links_by_goods = await export_deficiency_orders_links()
                # 导出后播放声音已导出
                logging.info("[自动导出] 已导出数量缺失的订单链接")
                # 播放声音提示
                play_sound()
                # for goods_name in CONFIG['NINGMENG_GOODS_NAMES']:
                #     links = deficiency_links_by_goods.get(goods_name, [])
                #     if links:
                #         for _ in range(3):  # 重试3次
                #             try:
                #                 result = ningmeng.refund_orders(links)
                #                 logging.info(f"[柠檬] 已为商品 {goods_name} 提交数量缺失订单退款申请，订单链接：{links}，返回结果：{result}")
                #                 break
                #             except Exception as e:
                #                 logging.error(f"[柠檬] 为商品 {goods_name} 提交数量缺失订单退款申请失败，订单链接：{links}，错误信息：{e}") 
                #                 continue
                interval = int(CONFIG["EXPORT_TIME_INTERVAL"])  # type: ignore
            else:
                interval = 60
            await asyncio.sleep(interval)  # type: ignore

    threading.Thread(target=lambda: asyncio.run(_runner()), daemon=True).start()
    
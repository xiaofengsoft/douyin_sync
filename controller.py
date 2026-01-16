import asyncio
import logging
import threading
import time
from typing import Dict, Any, List
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import CONFIG
from controllers.order_controller import query_order_refund_amount, query_finished_orders_for_monitor
from utils.douyin import batch_aweme_likes


async def bind_sanyecao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """绑定三叶草群组ID"""
    chat_id = update.effective_chat.id
    CONFIG["SANYECAO_GROUP_ID"] = chat_id
    await update.message.reply_text(f"✅ 已绑定三叶草群组ID: {chat_id}")
    logging.info(f"三叶草群组ID已绑定: {chat_id}")


async def bind_ningmeng(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """绑定柠檬群组ID"""
    chat_id = update.effective_chat.id
    CONFIG["NINGMENG_ID"] = chat_id
    await update.message.reply_text(f"✅ 已绑定柠檬群组ID: {chat_id}")
    logging.info(f"柠檬群组ID已绑定: {chat_id}")


async def query_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询总收入"""
    try:
        total = query_order_refund_amount()
        await update.message.reply_text(f"💰 当前总收入: ¥{total:.2f}")
        logging.info(f"查询总收入: {total:.2f}")
    except Exception as e:
        logging.error(f"查询总收入失败: {e}")
        await update.message.reply_text(f"❌ 查询失败: {e}")


async def auto_refund_task(app: Application):
    """自动退款定时任务：每小时运行一次"""
    while True:
        try:
            logging.info("开始执行自动退款任务")
            
            # 获取订单数据
            orders = query_finished_orders_for_monitor()
            if not orders:
                logging.info("没有需要处理的订单")
                continue
            
            # 批量获取当前点赞数
            current_real_nums = await batch_aweme_likes(orders)
            
            # 按商品名称分组缺失订单的链接
            ningmeng_links: List[str] = []
            sanyecao_by_goods: Dict[str, List[str]] = {}
            
            for i, order in enumerate(orders):
                order["current_num"] = current_real_nums[i]
                produced = order["current_num"] - order["start_num"]
                deficiency_num = order["order_num"] - produced
                
                if deficiency_num > 0:
                    link = order["link"]
                    goods_name = order["goods_name"] or "unknown"
                    
                    # 添加到柠檬列表
                    ningmeng_links.append(link)
                    
                    # 添加到三叶草分组
                    sanyecao_by_goods.setdefault(goods_name, []).append(link)
                    
                    logging.info(f"发现缺失订单: {link}, 缺失 {deficiency_num} 个")
            
            # 发送给柠檬
            ningmeng_id = CONFIG.get("NINGMENG_ID")
            if ningmeng_id and ningmeng_links:
                message = "售后\n" + "\n".join(ningmeng_links)
                try:
                    await app.bot.send_message(chat_id=ningmeng_id, text=message)
                    logging.info(f"已发送 {len(ningmeng_links)} 个链接到柠檬群组")
                except Exception as e:
                    logging.error(f"发送消息到柠檬群组失败: {e}")
            
            # 发送给三叶草（按商品名称分组）
            sanyecao_id = CONFIG.get("SANYECAO_GROUP_ID")
            if sanyecao_id and sanyecao_by_goods:
                for goods_name, links in sanyecao_by_goods.items():
                    message = f"售后\n{goods_name}\n" + "\n".join(links)
                    try:
                        await app.bot.send_message(chat_id=sanyecao_id, text=message)
                        logging.info(f"已发送 {len(links)} 个链接（商品：{goods_name}）到三叶草群组")
                    except Exception as e:
                        logging.error(f"发送消息到三叶草群组失败: {e}")
            
            logging.info("自动退款任务执行完成")
            
        except Exception as e:
            logging.error(f"自动退款任务异常: {e}")
        await asyncio.sleep(3600)  # 等待1小时


def start_bot():
    """启动 Telegram Bot"""
    bot_token = str(CONFIG.get("TELEGRAM_BOT_TOKEN"))
    if not bot_token:
        logging.error("未配置 TELEGRAM_BOT_TOKEN，无法启动 Bot")
        return
    
    # 创建应用
    app = Application.builder().token(bot_token).build()
    
    # 注册命令处理器
    app.add_handler(CommandHandler("bind_sanyecao", bind_sanyecao))
    app.add_handler(CommandHandler("bind_ningmeng", bind_ningmeng))
    app.add_handler(CommandHandler("query_income", query_income))
    
    logging.info("Telegram Bot 命令已注册")
    
    # 在单独线程中启动定时任务
    def run_auto_refund():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(auto_refund_task(app))
    
    refund_thread = threading.Thread(target=run_auto_refund, daemon=True)
    refund_thread.start()
    logging.info("自动退款定时任务已启动（每小时执行一次）")
    
    # 启动 Bot（阻塞运行）
    logging.info("启动 Telegram Bot...")
    app.run_polling()


if __name__ == "__main__":
    start_bot()

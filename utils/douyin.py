import os
import asyncio
import httpx
import aiofiles
from tikhub import Client
from config import CONFIG
import time
import logging

# 初始化 TikHub 客户端 | Initialize TikHub client
tikhub = Client(api_key=str(CONFIG["TIKHUB_API_KEY"]))


# 获取视频信息 | Get video info
async def get_aweme_likes(aweme_share_url: str):
    try:
        info = await tikhub.DouyinAppV3.fetch_one_video_by_share_url(aweme_share_url)
        info = info["data"]["aweme_detail"]  # type: ignore
        digg_count = info["statistics"]["digg_count"]
        return digg_count
    except KeyError as e:
        logging.error(f"Error retrieving video info: {e}")
        return None


# 批量获取视频点赞数 | Batch get video likes
async def batch_aweme_likes(orders: list) -> list:
    # 每次执行10个请求 | Execute 10 requests at a time
    batch_size = 10
    results = []
    i = 0
    while i < len(orders):
        # 如果剩余订单少于 batch_size，则调整大小 | Adjust size if remaining orders are less than batch_size
        current_batch_size = min(batch_size, len(orders) - i)
        tasks = [get_aweme_likes(o["link"]) for o in orders[i : i + current_batch_size]]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        i += current_batch_size
        await asyncio.sleep(10)  # 避免请求过快 | Avoid making requests too quickly
    return results

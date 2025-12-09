# 展开短链接
import requests
import re
import datetime
import json
from urllib.parse import unquote
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from utils.owlproxy import owlproxy
from config import CONFIG


def expand_short_url(short_url, proxy=None):
    if "v.douyin.com" in short_url:
        try:
            response = requests.get(
                short_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                },
                allow_redirects=True,
                timeout=10,
                proxies=proxy,
            )
            url = response.url
            return url
        except requests.RequestException as e:
            print(f"Error expanding short URL: {e}")
            return ""


async def expand_short_url_async(session: aiohttp.ClientSession, short_url: str, proxy_url: Optional[str]) -> str:
    if "v.douyin.com" in short_url:
        try:
            async with session.get(
                short_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                },
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=10),
                proxy=proxy_url,
            ) as resp:
                return str(resp.url)
        except Exception as e:
            logging.error(f"短链展开失败: {e}")
            return ""
    return short_url


def extract_video_id(url):
    """从抖音视频链接中提取视频ID。"""
    patterns = [
        r"/video/(\d+)",
        r"/share/video/(\d+)",
        r"aweme_id=(\d+)",
        r"modal_id=(\d+)",
        r"/(\d{19})/",  # 19位数字ID
        r"/(\d{18})/",  # 18位数字ID
        r"item_ids=(\d+)",
        r"/note/(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    current_millis = int(datetime.datetime.now().timestamp() * 1000)
    print(f"无法从链接中提取视频ID，使用当前时间戳作为备用ID: {current_millis}")
    return str(current_millis)


def _decode_response(resp) -> str:
    """简化版：仅处理 br 压缩，其他情况直接返回 resp.text"""
    try:
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if "br" in enc:
            import brotli

            raw = resp.content or b""
            return brotli.decompress(raw).decode("utf-8", errors="ignore")
        return resp.text or ""
    except Exception:
        try:
            return resp.text or (
                resp.content.decode("utf-8", errors="ignore") if resp.content else ""
            )
        except Exception:
            return ""


async def _decode_response_async(resp: aiohttp.ClientResponse) -> str:
    try:
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        raw = await resp.read()
        if "br" in enc:
            import brotli
            return brotli.decompress(raw or b"").decode("utf-8", errors="ignore")
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return await resp.text()
    except Exception:
        try:
            return await resp.text()
        except Exception:
            return ""


def parse_video_id_from_url(url, video_id, proxy=None):
    """Python版的 parseVideoFromHtml，解析页面统计数据与视频信息"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        resp = requests.get(
            url, headers=headers, timeout=15, proxies=proxy, allow_redirects=True
        )
        print("成功获取视频页面")
        # 使用通用解码，避免直接打印 resp.text 导致乱码
        html = _decode_response(resp)
        # 基础字段尝试（可能用于兜底显示）
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        desc_match = re.search(r'data-desc="([^"]+)"', html) or re.search(
            r'description[^>]*content="([^"]+)"', html
        )
        author_match = re.search(r'data-author="([^"]+)"', html) or re.search(
            r'"nickname":"([^"]+)"', html
        )

        # 解析 window._ROUTER_DATA
        router_data = None
        try:
            m = re.search(
                r"window\._ROUTER_DATA\s*=\s*({.+?});", html, re.S
            ) or re.search(r"window\._ROUTER_DATA\s*=\s*({.+?})</script>", html, re.S)
            if m:
                print("成功解析 window._ROUTER_DATA")
                router_data = json.loads(m.group(1))
        except Exception:
            router_data = None

        # 统计字段
        like_count = 0
        comment_count = 0
        share_count = 0
        play_count = 0
        collect_count = 0
        forward_count = 0

        # 优先从 _ROUTER_DATA 提取统计
        try:
            if router_data:
                loader = router_data.get("loaderData", {})
                page = (
                    loader.get("video_(id)/page", {})
                    if isinstance(loader, dict)
                    else {}
                )
                info = page.get("videoInfoRes", {}) if isinstance(page, dict) else {}
                item_list = info.get("item_list") or []
                if isinstance(item_list, list) and item_list:
                    stats = item_list[0].get("statistics") or {}
                    like_count = int(stats.get("digg_count") or 0)
                    comment_count = int(stats.get("comment_count") or 0)
                    share_count = int(stats.get("share_count") or 0)
                    play_count = int(stats.get("play_count") or 0)
                    collect_count = int(stats.get("collect_count") or 0)
                    forward_count = int(stats.get("forward_count") or 0)
        except Exception:
            pass

        # 备用：从HTML中直接匹配
        if like_count == 0 and re.search(r'"digg_count":\s*\d+', html):

            def pick_int(pattern):
                m = re.search(pattern, html)
                return int(m.group(1)) if m else 0

            like_count = pick_int(r'"digg_count":\s*(\d+)')
            comment_count = pick_int(r'"comment_count":\s*(\d+)')
            share_count = pick_int(r'"share_count":\s*(\d+)')
            play_count = pick_int(r'"play_count":\s*(\d+)')
            collect_count = pick_int(r'"collect_count":\s*(\d+)')
            forward_count = pick_int(r'"forward_count":\s*(\d+)')

        # 提取视频URL（优先 _ROUTER_DATA）
        video_url = None
        extracted_video_id = None
        try:
            if router_data:
                loader = router_data.get("loaderData", {})
                page = (
                    loader.get("video_(id)/page", {})
                    if isinstance(loader, dict)
                    else {}
                )
                info = page.get("videoInfoRes", {}) if isinstance(page, dict) else {}
                item_list = info.get("item_list") or []
                if isinstance(item_list, list) and item_list:
                    video_obj = item_list[0].get("video") or {}
                    extracted_video_id = video_obj.get("play_addr", {}).get("uri")
                    if extracted_video_id:
                        video_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={extracted_video_id}&ratio=720p&line=0"
        except Exception:
            pass

        # 备用：从HTML拼接/提取
        if not video_url:
            m = re.search(r'"video":\{"play_addr":\{[^}]+"url_list":\["([^"]+)"', html)
            original_url = m.group(1) if m else None
            if not original_url:
                m = re.search(r'"play_addr":\{"url_list":\["([^"]+)"', html)
                original_url = m.group(1) if m else None
            if original_url:
                original_url = original_url.replace(r"\u002F", "/")
                original_url = unquote(original_url)
                vid_m = re.search(r"video_id=([^&]+)", original_url)
                if vid_m:
                    extracted_video_id = vid_m.group(1)
                    video_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={extracted_video_id}&ratio=720p&line=0"
                else:
                    video_url = original_url

        # 封面与音乐信息
        cover_m = re.search(r'"cover":\{"url_list":\["([^"]+)"', html)
        cover_url = cover_m.group(1) if cover_m else None

        music_title_m = re.search(r'"music":\{"title":"([^"]+)"', html)
        music_author_m = re.search(r'"music":\{"author":"([^"]+)"', html)
        music_url_m = re.search(r'"music":\{"play_url":\{"url_list":\["([^"]+)"', html)

        # 标签
        hashtags = []
        for m in re.findall(r'"hashtag_name":"([^"]+)"', html):
            hashtags.append(m)

        result = {
            "success": True,
            "author": author_match.group(1) if author_match else "未知作者",
            "authorId": "",
            "publishTime": datetime.datetime.now().strftime("%Y-%m-%d"),
            "likeCount": like_count,
            "commentCount": comment_count,
            "shareCount": share_count,
            "playCount": play_count,
            "collectCount": collect_count,
            "forwardCount": forward_count,
            "description": (desc_match.group(1) if desc_match else "无描述"),
            "videoUrl": video_url,
            "coverUrl": cover_url,
            "videoId": extracted_video_id or video_id,
            "duration": 0,
            "width": 0,
            "height": 0,
            "musicTitle": music_title_m.group(1) if music_title_m else "",
            "musicAuthor": music_author_m.group(1) if music_author_m else "",
            "musicUrl": music_url_m.group(1) if music_url_m else "",
            "hashtags": hashtags,
        }
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def parse_video_id_from_url_async(session: aiohttp.ClientSession, url: str, video_id: str, proxy_url: Optional[str]) -> Dict[str, Any]:
    """异步解析页面统计数据与视频信息"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        async with session.get(
            url, headers=headers, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15), proxy=proxy_url
        ) as resp:
            logging.info("成功获取视频页面")
            html = await _decode_response_async(resp)

        # 基础字段尝试（可能用于兜底显示）
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        desc_match = re.search(r'data-desc="([^"]+)"', html) or re.search(
            r'description[^>]*content="([^"]+)"', html
        )
        author_match = re.search(r'data-author="([^"]+)"', html) or re.search(
            r'"nickname":"([^"]+)"', html
        )

        # 解析 window._ROUTER_DATA
        router_data = None
        try:
            m = re.search(
                r"window\._ROUTER_DATA\s*=\s*({.+?});", html, re.S
            ) or re.search(r"window\._ROUTER_DATA\s*=\s*({.+?})</script>", html, re.S)
            if m:
                logging.info("成功解析 window._ROUTER_DATA")
                router_data = json.loads(m.group(1))
        except Exception:
            router_data = None

        # 统计字段
        like_count = 0
        comment_count = 0
        share_count = 0
        play_count = 0
        collect_count = 0
        forward_count = 0

        # 优先从 _ROUTER_DATA 提取统计
        try:
            if router_data:
                loader = router_data.get("loaderData", {})
                page = (
                    loader.get("video_(id)/page", {})
                    if isinstance(loader, dict)
                    else {}
                )
                info = page.get("videoInfoRes", {}) if isinstance(page, dict) else {}
                item_list = info.get("item_list") or []
                if isinstance(item_list, list) and item_list:
                    stats = item_list[0].get("statistics") or {}
                    like_count = int(stats.get("digg_count") or 0)
                    comment_count = int(stats.get("comment_count") or 0)
                    share_count = int(stats.get("share_count") or 0)
                    play_count = int(stats.get("play_count") or 0)
                    collect_count = int(stats.get("collect_count") or 0)
                    forward_count = int(stats.get("forward_count") or 0)
        except Exception:
            pass

        # 备用：从HTML中直接匹配
        if like_count == 0 and re.search(r'"digg_count":\s*\d+', html):

            def pick_int(pattern):
                m = re.search(pattern, html)
                return int(m.group(1)) if m else 0

            like_count = pick_int(r'"digg_count":\s*(\d+)')
            comment_count = pick_int(r'"comment_count":\s*(\d+)')
            share_count = pick_int(r'"share_count":\s*(\d+)')
            play_count = pick_int(r'"play_count":\s*(\d+)')
            collect_count = pick_int(r'"collect_count":\s*(\d+)')
            forward_count = pick_int(r'"forward_count":\s*(\d+)')

        # 提取视频URL（优先 _ROUTER_DATA）
        video_url = None
        extracted_video_id = None
        try:
            if router_data:
                loader = router_data.get("loaderData", {})
                page = (
                    loader.get("video_(id)/page", {})
                    if isinstance(loader, dict)
                    else {}
                )
                info = page.get("videoInfoRes", {}) if isinstance(page, dict) else {}
                item_list = info.get("item_list") or []
                if isinstance(item_list, list) and item_list:
                    video_obj = item_list[0].get("video") or {}
                    extracted_video_id = video_obj.get("play_addr", {}).get("uri")
                    if extracted_video_id:
                        video_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={extracted_video_id}&ratio=720p&line=0"
        except Exception:
            pass

        # 备用：从HTML拼接/提取
        if not video_url:
            m = re.search(r'"video":\{"play_addr":\{[^}]+"url_list":\["([^"]+)"', html)
            original_url = m.group(1) if m else None
            if not original_url:
                m = re.search(r'"play_addr":\{"url_list":\["([^"]+)"', html)
                original_url = m.group(1) if m else None
            if original_url:
                original_url = original_url.replace(r"\u002F", "/")
                original_url = unquote(original_url)
                vid_m = re.search(r"video_id=([^&]+)", original_url)
                if vid_m:
                    extracted_video_id = vid_m.group(1)
                    video_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={extracted_video_id}&ratio=720p&line=0"
                else:
                    video_url = original_url

        # 封面与音乐信息
        cover_m = re.search(r'"cover":\{"url_list":\["([^"]+)"', html)
        cover_url = cover_m.group(1) if cover_m else None

        music_title_m = re.search(r'"music":\{"title":"([^"]+)"', html)
        music_author_m = re.search(r'"music":\{"author":"([^"]+)"', html)
        music_url_m = re.search(r'"music":\{"play_url":\{"url_list":\["([^"]+)"', html)

        # 标签
        hashtags = []
        for m in re.findall(r'"hashtag_name":"([^"]+)"', html):
            hashtags.append(m)

        result = {
            "success": True,
            "author": author_match.group(1) if author_match else "未知作者",
            "authorId": "",
            "publishTime": datetime.datetime.now().strftime("%Y-%m-%d"),
            "likeCount": like_count,
            "commentCount": comment_count,
            "shareCount": share_count,
            "playCount": play_count,
            "collectCount": collect_count,
            "forwardCount": forward_count,
            "description": (desc_match.group(1) if desc_match else "无描述"),
            "videoUrl": video_url,
            "coverUrl": cover_url,
            "videoId": extracted_video_id or video_id,
            "duration": 0,
            "width": 0,
            "height": 0,
            "musicTitle": music_title_m.group(1) if music_title_m else "",
            "musicAuthor": music_author_m.group(1) if music_author_m else "",
            "musicUrl": music_url_m.group(1) if music_url_m else "",
            "hashtags": hashtags,
        }
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_proxy_url(model) -> str:
    """将 OwlProxyModel 转换为 aiohttp 可用的代理URL"""
    scheme = (getattr(model, "proxyType", None) or "http").lower()
    host = getattr(model, "proxyHost", "")
    port = getattr(model, "proxyPort", 0)
    user = getattr(model, "userName", "")
    pwd = getattr(model, "password", "")
    auth = f"{user}:{pwd}@" if user and pwd else ""
    # host 可能已包含端口（如 change5.owlproxy.com:7778），优先使用 proxyHost+port 组合
    if ":" in host and port == 0:
        host_port = host
    else:
        host_port = f"{host}:{port}"
    return f"{scheme}://{auth}{host_port}"


def _proxy_label(model) -> str:
    """用于日志的代理标识，避免输出账号信息"""
    scheme = (getattr(model, "proxyType", None) or "http").lower()
    host = getattr(model, "proxyHost", "")
    port = getattr(model, "proxyPort", 0)
    if ":" in host and port == 0:
        host_port = host
    else:
        host_port = f"{host}:{port}"
    return f"{scheme}://{host_port}"


async def _fetch_like_with_retry(session: aiohttp.ClientSession, link: str, proxies: List, attempt_proxies_per_task: List) -> int:
    """对单个链接尝试最多3次，分别使用不同代理。成功返回点赞数，失败返回正无穷"""
    for i in range(3):
        proxy_model = attempt_proxies_per_task[i % len(attempt_proxies_per_task)]
        proxy_url = _build_proxy_url(proxy_model)
        label = _proxy_label(proxy_model)
        try:
            logging.info(f"[尝试 {i+1}/3] 使用代理 {label} 抓取: {link}")
            expanded_url = await expand_short_url_async(session, link, proxy_url)
            video_id = extract_video_id(expanded_url or link)
            info = await parse_video_id_from_url_async(session, expanded_url or link, video_id, proxy_url)
            if info.get("success"):
                like_cnt = int(info.get("likeCount", 0))
                logging.info(f"[成功] 代理 {label} 获取点赞数: {like_cnt}")
                return like_cnt
            else:
                logging.warning(f"[失败] 代理 {label} 解析失败: {info.get('error')}")
        except Exception as e:
            logging.error(f"[异常] 代理 {label} 第 {i+1} 次失败: {e}")
            continue
    logging.error(f"[放弃] 链接重试3次失败: {link}")
    return float("inf")


async def batch_aweme_likes(orders: List[Dict[str, Any]]) -> List[int]:
    """批量并发获取点赞数（aiohttp），每次请求使用不同代理，失败返回正无穷。并发度受限于 CONFIG['IO_WORKERS_NUM']"""
    orders = orders or []
    if not orders:
        return []

    max_workers_cfg = int(CONFIG.get("IO_WORKERS_NUM", 10))
    max_workers = max(1, min(max_workers_cfg, len(orders)))
    logging.info(f"开始批量获取点赞数：共 {len(orders)} 个订单，并发度 {max_workers}")

    # 创建足够数量的动态代理
    need = max(len(orders), 1)
    result = owlproxy.create_dynamic_proxies(good_num=need)
    proxies = result.data or []
    logging.info(f"已创建动态代理数量: {len(proxies)} (需求 {need})")
    if not proxies:
        logging.error("未能创建任何代理，返回正无穷")
        return [float("inf")] * len(orders)

    # 为每个任务分配至少一个不同代理；若不足则循环复用（每个任务最多分配3个候选代理用于重试）
    per_task_proxies = []
    for idx in range(len(orders)):
        candidates = [proxies[(idx + k) % len(proxies)] for k in range(min(3, len(proxies)))]
        per_task_proxies.append(candidates)
        labels = ", ".join(_proxy_label(p) for p in candidates)
        logging.debug(f"任务 {idx} 分配代理: {labels}")

    timeout = aiohttp.ClientTimeout(total=20)
    connector = aiohttp.TCPConnector(limit=max_workers, ssl=False)
    sem = asyncio.Semaphore(max_workers)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        async def limited_fetch(i: int, o: Dict[str, Any]):
            async with sem:
                return await _fetch_like_with_retry(session, (o.get("link") or ""), proxies, per_task_proxies[i])

        tasks = [limited_fetch(i, o) for i, o in enumerate(orders)]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    logging.info("批量获取完成")
    return results


if __name__ == "__main__":
    # 测试代码

    test_short_url = "https://v.douyin.com/vDf2Pqlqd9M/"

    print(test_url := expand_short_url(test_short_url))
    print(video_id := extract_video_id(test_url))
    print(parse_video_id_from_url(test_url, video_id))

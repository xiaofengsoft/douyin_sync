# 展开短链接
import requests
import re
import datetime
import json
from urllib.parse import unquote


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


def batch_get_digg_count(orders):
    """批量获取点赞数"""
    results = []
    for order in orders:
        link = order.get("link")
        if not link:
            results.append(None)
            continue
        expanded_url = expand_short_url(link)
        video_id = extract_video_id(expanded_url)
        info = parse_video_id_from_url(expanded_url, video_id)
        if info.get("success"):
            results.append(info.get("likeCount", 0))
        else:
            results.append(None)
    return results


if __name__ == "__main__":
    # 测试代码

    test_short_url = "https://v.douyin.com/vDf2Pqlqd9M/"

    print(test_url := expand_short_url(test_short_url))
    print(video_id := extract_video_id(test_url))
    print(parse_video_id_from_url(test_url, video_id))

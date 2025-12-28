import base64
import requests
from config import CONFIG
YUNMA_TOKEN = CONFIG["YUNMA_TOKEN"]


def verify(image_path, type = "10103"):
    """
    云码识别
    :param image_path: 可以是本地路径,也可以是网络图片
    :param type: 10110 4位纯数字, 10111 4
    """
    b = None
    if image_path.startswith("http") or image_path.startswith("https"):
        response = requests.get(image_path)
        b = base64.b64encode(response.content).decode()
    else:
        with open(image_path, "rb") as f:
            b = base64.b64encode(f.read()).decode()
    return verify_base64(b, type)


def verify_base64(image_base64, type = "10103"):
    """
    云码识别
    :param image_base64: 图片的base64字符串
    :param type: 10110 4位纯数字, 10111 4
    """
    url = "http://api.jfbym.com/api/YmServer/customApi"
    data = {
        ## 关于参数,一般来说有3个;不同类型id可能有不同的参数个数和参数名,找客服获取
        "token": YUNMA_TOKEN,
        "type": type,
        "image": image_base64,
    }
    _headers = {
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, headers=_headers, json=data).json()
    return response["data"]['data']
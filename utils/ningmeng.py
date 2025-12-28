import requests
import json
import sys

import os
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from config import CONFIG
from utils.crypt import encrypt
from utils.yunma import verify_base64

class NingMengAPI:
    def __init__(self, username: str, encrypted_password: str, iv: str) -> None:
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": "https://www.ningmeng88.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.ningmeng88.com",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
        }
        self.cookies = {
            "session_id": ""
        }
        self.username = username
        self.encrypted_password = encrypted_password
        self.iv = iv

    def retry_post(self, url: str, data: dict, max_retries: int = 3) -> requests.Response | None:
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=self.headers, cookies=self.cookies, data=json.dumps(data, separators=(',', ':')))
                response.raise_for_status()  # 检查响应状态码是否为 200
                return response
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    continue  # 重试
                else:
                    raise e  # 达到最大重试次数，抛出异常
        
    def captcha(self):
        url = "https://www.ningmeng88.com/web/captcha/info"
        response = self.retry_post(url, {})
        ret_json = response.json()
        return {
          "captcha_img_base64": ret_json["data"]["captcha"],
          "token": ret_json["data"]["token"]
        }
        
    def login(self):
        url = "https://www.ningmeng88.com/web/user/login"
        # pwd_enc = encrypt(CONFIG["NINGMENG_PASSWORD"])
        for _ in range(10): 
            captcha_info = self.captcha()
            data = {
                "user_name": self.username,
                # "password": pwd_enc['ciphertext'],
                # "iv": pwd_enc['iv'],
                "password": self.encrypted_password,
                "iv": self.iv,
                "captcha": verify_base64(captcha_info["captcha_img_base64"]),
                "captcha_token": captcha_info["token"]
            }
            response = self.retry_post(url, data)
            # 获取set-cookie中的session_id
            res_json = response.json()
            if res_json["status_code"] == 400:
                continue
            self.cookies["session_id"] = str(response.cookies.get("session_id"))
        

    def query_order(self, receive_order: str = "", order_link: str = "", page: int = 1, page_size: int = 10):
        self.login()
        url = "https://www.ningmeng88.com/web/refund/list/partner"
        data = {
            "page": page,
            "page_size": page_size,
        }
        if receive_order:
            data["receive_order"] = receive_order
        if order_link:
            data["order_link"] = order_link
        response = self.retry_post(url, data)
        return response.json()["data"]


    def refund_orders(self, order_links: list):
        self.login()
        url = "https://www.ningmeng88.com/web/refund/save/partner"
        data = {
            "order_link": order_links
        }
        response = self.retry_post(url, data)
        response_json = response.json()
        if not (response_json["status_code"] == 200 or response_json["status_code"] == 206):
            raise Exception(f"[柠檬] 提交退款申请失败，错误信息：{response_json['msg']}")
        return response_json["message"]

ningmeng = NingMengAPI(str(CONFIG["NINGMENG_USERNAME"]), str(CONFIG["NINGMENG_ENCRYPTION_KEY"]), str(CONFIG["NINGMENG_ENCRYPTION_IV"]))

if __name__ == "__main__":
    orders = """
    """.strip().split("\n")
    # result = ningmeng.refund_orders(orders)
    result = ningmeng.query_order(page=1, page_size=100)
    print(result)
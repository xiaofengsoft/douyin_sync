import datetime
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional, List, Tuple
import binascii
from urllib.parse import urlencode
from config import CONFIG
import requests
import os
from models.owlproxy import OwlProxyDynamicProxyResult, OwlProxyResult, OwlProxyModel

# VMOS API配置
SERVICE = "armcloud-paas"
CONTENT_TYPE = "application/json;charset=UTF-8"
SIGNED_HEADERS = "content-type;host;x-content-sha256;x-date"

# API密钥配置
ACCESS_KEY_ID = CONFIG["OWLPROXY_KEY_ID"]
SECRET_ACCESS_KEY = CONFIG["OWLPROXY_KEY_SECRET"]
# --- End 配置 ---


class PaasSigner:
    """封装签名逻辑的静态工具类"""

    @staticmethod
    def _hmac_sha256(key: bytes, content: str) -> bytes:
        """执行 HMAC-SHA256 计算，内容编码为 UTF-8"""
        return hmac.new(key, content.encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def _gen_signing_secret_key_v4(secret_key: str, date: str) -> bytes:
        """密钥派生过程"""
        k_date = PaasSigner._hmac_sha256(secret_key.encode("utf-8"), date)
        k_service = PaasSigner._hmac_sha256(k_date, SERVICE)
        return PaasSigner._hmac_sha256(k_service, "request")

    @staticmethod
    def calculate_signature(
        body_string: str,
        x_date: str,
        host: str,
        content_type: str,
        signed_headers: str,
        sk: str,
        is_debugging: bool = False,
    ) -> Tuple[str, str]:
        """
        核心签名逻辑，接收 body 字符串，并根据 is_debugging 输出详细日志。
        返回: (signature, x_content_sha256)
        """

        body_bytes = body_string.encode("utf-8")

        # 1. 计算 x-content-sha256
        x_content_sha256 = hashlib.sha256(body_bytes).hexdigest()

        # 2. **关键修复：** 去除 content-type 中的空格
        content_type_clean = content_type.replace(" ", "")

        # 获取 shortXDate
        short_x_date = x_date[:8]

        # 3. 构建 Canonical Request
        # API 服务器似乎期望 host 为 'null'，这是基于您旧的 Java 日志的关键修复
        canonical_host = "null"

        canonical_string_builder = (
            f"host:{canonical_host}\n"
            f"x-date:{x_date}\n"
            f"content-type:{content_type_clean}\n"
            f"signedHeaders:{signed_headers}\n"
            f"x-content-sha256:{x_content_sha256}"
        )

        # 4. 计算 Canonical Request 的 SHA-256 散列
        hash_canonical_string = hashlib.sha256(
            canonical_string_builder.encode("utf-8")
        ).hexdigest()

        # 5. 构建 String To Sign
        credential_scope = f"{short_x_date}/{SERVICE}/request"

        sign_string = (
            "HMAC-SHA256"
            + "\n"
            + x_date
            + "\n"
            + credential_scope
            + "\n"
            + hash_canonical_string
        )

        # 6. 派生 Signing Key
        signing_key = PaasSigner._gen_signing_secret_key_v4(sk, short_x_date)

        # 7. 计算最终签名
        signature_bytes = hmac.new(
            signing_key, sign_string.encode("utf-8"), hashlib.sha256
        ).digest()

        # 8. 转换为十六进制字符串
        signature = binascii.hexlify(signature_bytes).decode("utf-8")
        return signature, x_content_sha256


class OWLService:

    def __init__(self, access_key_id: str = None, secret_access_key: str = None):
        self.access_key_id = access_key_id or ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or SECRET_ACCESS_KEY

    def _prepare_request_data(
        self, method: str, data: Dict[str, Any]
    ) -> Tuple[str, Optional[bytes], Optional[Dict[str, Any]]]:
        """准备签名 body 字符串、请求 body 字节和查询参数字典"""

        if method.upper() == "GET":
            # GET 请求的签名 body 是 URL 查询参数字符串
            signature_body_string = urlencode(data) if data else ""
            request_data = None
            request_params = data
        else:
            # POST/PUT/DELETE：签名 body 为压缩后的 JSON 字符串
            if not data:
                data = {}
            signature_body_string = json.dumps(
                data, separators=(",", ":"), ensure_ascii=False
            )
            request_data = signature_body_string.encode("utf-8")
            request_params = None

        return signature_body_string, request_data, request_params

    def owl_request(
        self, url: str, data: Dict[str, Any], method: str = "POST", timeout: int = 30
    ) -> OwlProxyResult:
        """通用VMOS请求方法"""

        x_date = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        # 1. 准备数据和签名 body
        signature_body_string, request_data, request_params = (
            self._prepare_request_data(method, data)
        )

        host = "api.owlproxy.com"

        # 2. 计算签名和 x-content-sha256
        signature, x_content_sha256 = PaasSigner.calculate_signature(
            body_string=signature_body_string,
            x_date=x_date,
            host=host,
            content_type=CONTENT_TYPE,
            signed_headers=SIGNED_HEADERS,
            sk=self.secret_access_key,
        )

        # 3. 构建 Header 和 URL
        short_date = x_date[:8]
        full_url = f"https://{host}{url}"

        headers = {
            "content-type": CONTENT_TYPE,
            "host": host,
            "x-content-sha256": x_content_sha256,
            "x-date": x_date,
            "authorization": (
                f"HMAC-SHA256 Credential={self.access_key_id}/{short_date}/{SERVICE}/request, "
                f"SignedHeaders={SIGNED_HEADERS}, "
                f"Signature={signature}"
            ),
        }

        # 4. 发送请求
        response = requests.request(
            method,
            full_url,
            headers=headers,
            data=request_data,
            params=request_params,
            timeout=timeout,
        )
        response.raise_for_status()
        return OwlProxyResult(**response.json())

    def create_dynamic_proxies(
        self,
        good_num: int = 100,
        country_code: str = CONFIG["OWLPROXY_COUNTRY"],
        state: str = "",
        city: str = "",
        proxy_host: str = "change5.owlproxy.com:7778",
        proxy_type: str = "http",
        time_minutes: int = int(CONFIG["OWLPROXY_LIFETIME"]) // 60,
    ) -> OwlProxyDynamicProxyResult:
        """
        调用 /openApi/vcDynamicGood/createProxy，返回格式化列表，单项为 dict:
        { "ip": ..., "port": ..., "user": ..., "pwd": ..., "proxyType": ..., "raw": {...} }
        """
        # owlproxy一次只能最多创建50个代理，所以要分批创建
        body = {
            "countryCode": country_code,
            "state": state,
            "city": city,
            "proxyHost": proxy_host,
            "proxyType": proxy_type,
            "time": time_minutes,
            "goodNum": good_num,
        }
        if good_num > 50:
            real_ret = OwlProxyDynamicProxyResult(
                code=0, msg="批量创建代理开始", ts=0, data=[]
            )
            while good_num > 0:
                num = 50 if good_num >= 50 else good_num
                body = {
                    "countryCode": country_code,
                    "state": state,
                    "city": city,
                    "proxyHost": proxy_host,
                    "proxyType": proxy_type,
                    "time": time_minutes,
                    "goodNum": num,
                }
                ret = self.owl_request(
                    "/owlproxy/api/openApi/vcDynamicGood/createProxy", body, "POST"
                )
                result = OwlProxyDynamicProxyResult(**ret.model_dump())
                good_num -= 50
                real_ret.data.extend(result.data)
                time.sleep(1)  # 避免请求过快
            return real_ret

        else:
            ret = self.owl_request(
                "/owlproxy/api/openApi/vcDynamicGood/createProxy", body, "POST"
            )
            result = OwlProxyDynamicProxyResult(**ret.model_dump())
            return result


owlproxy = OWLService()

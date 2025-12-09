import os
import logging
import json
import threading

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORT_DIR = os.path.join(DATA_DIR, "exported")


CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# 日志配置
LOG_PATH = os.path.join(DATA_DIR, "app.log")
LOG_LEVEL = "INFO"
logging.basicConfig(
    filename=LOG_PATH,
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# ---------------- CONFIG 动态读写支持 ----------------

_config_lock = threading.RLock()


def _load_config_dict() -> dict:
    """从 CONFIG_PATH 读取配置字典，不做结构转换，原样返回。"""
    with _config_lock:
        if not os.path.exists(CONFIG_PATH):
            return {}
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_config_dict(data: dict) -> None:
    """将配置字典写回 CONFIG_PATH。"""
    with _config_lock:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class Config:
    """
    一个简单的配置对象：
    - 支持 dict 风格访问: CONFIG["EXPORT_TIME_INTERVAL"]
      => 直接得到该配置项的 value 值
    - 支持属性访问: CONFIG.EXPORT_TIME_INTERVAL  (见 __getattr__)
    - 如需获取完整信息使用: CONFIG.get_info("EXPORT_TIME_INTERVAL")
    - 每次写操作都会立即持久化到 config.json
    """

    def __init__(self, initial: dict | None = None):
        self._lock = _config_lock
        self._data = initial or {}

    # ---- dict 接口 ----
    def __getitem__(self, key):
        """直接返回对应 key 下的 value 字段。"""
        with self._lock:
            item = self._data[key]
            if isinstance(item, dict) and "value" in item:
                return item["value"]
            return item

    def __setitem__(self, key, value):
        with self._lock:
            # 如果原来是 dict，则只更新 value 字段；否则直接替换
            if key in self._data and isinstance(self._data[key], dict):
                self._data[key]["value"] = value
            else:
                self._data[key] = {"value": value}
            _save_config_dict(self._data)

    def __delitem__(self, key):
        with self._lock:
            del self._data[key]
            _save_config_dict(self._data)

    def get(self, key, default=None):
        """与 __getitem__ 语义一致：返回 value，找不到则返回 default。"""
        with self._lock:
            if key not in self._data:
                return default
            item = self._data[key]
            if isinstance(item, dict) and "value" in item:
                return item["value"]
            return item

    def items(self):
        """返回 (key, value) 对，value 为该 key 的 value 字段。"""
        with self._lock:
            result = []
            for k, v in self._data.items():
                if isinstance(v, dict) and "value" in v:
                    result.append((k, v["value"]))
                else:
                    result.append((k, v))
            return result

    def keys(self):
        with self._lock:
            return list(self._data.keys())

    def values(self):
        """仅返回各项的 value 字段。"""
        with self._lock:
            vals = []
            for v in self._data.values():
                if isinstance(v, dict) and "value" in v:
                    vals.append(v["value"])
                else:
                    vals.append(v)
            return vals

    def get_info(self, key, default=None):
        """
        返回该 key 下的完整信息（通常包含 value, desc 等）。
        如: CONFIG.get_info("TIKHUB_API_KEY")
        """
        with self._lock:
            return self._data.get(key, default)

    def reload(self):
        """手动从文件重新加载（可选，用于检测外部修改）。"""
        with self._lock:
            self._data = _load_config_dict()

    def to_dict(self) -> dict:
        """返回当前配置底层原始字典的浅拷贝（包含 value/desc 等）。"""
        with self._lock:
            return dict(self._data)


# 全局 CONFIG 常量：程序运行期间共享一份内存配置，写入时自动持久化
CONFIG = Config(_load_config_dict())

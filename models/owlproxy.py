from pydantic import BaseModel, Field
from typing import List, Sequence, Iterable
import logging


class OwlProxyResult(BaseModel):
    code: int = 0
    msg: str = ""
    ts: int = 0
    data: object | Sequence | List | None = None


class OwlProxyModel(BaseModel):
    proxyHost: str
    proxyPort: int
    userName: str
    password: str
    proxyType: str  # 协议类型：http、https、socks5


class OwlProxyDynamicProxyResult(OwlProxyResult):
    # 使用 Field(default_factory=list) 避免多个实例共享一个列表 & 触发子模型校验
    data: List[OwlProxyModel] = Field(default_factory=list)

    def safe_add(self, item):
        """单条追加，自动将 dict -> OwlProxyModel"""
        if isinstance(item, OwlProxyModel):
            self.data.append(item)
        elif isinstance(item, dict):
            try:
                self.data.append(OwlProxyModel(**item))
            except Exception as e:
                logging.warning(f"忽略无效代理项: {item} err={e}")
        else:
            logging.warning(f"未知类型代理项被忽略: {item}")

    def safe_extend(self, items: Iterable):
        """批量追加，保持类型安全"""
        for it in items or []:
            self.safe_add(it)

    @classmethod
    def from_raw_list(cls, items: Iterable):
        """一次性把原始列表转换为规范结果对象"""
        inst = cls()
        inst.safe_extend(items)
        return inst

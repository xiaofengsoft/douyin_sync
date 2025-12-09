from typing import Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Text,
    Numeric,
    UniqueConstraint,
    Index,
)

ORDER_STATUS_MAP = {
    -1: "待付款",
    1: "已付款",
    2: "处理中",
    3: "异常",
    4: "已完成",
    5: "退单中",
    6: "已退单",
    7: "已退款",
    8: "待处理",
}


class Order(SQLModel, table=True):
    __tablename__ = "order"

    id: Optional[int] = Field(default=None, primary_key=True, description="主键")
    create_at: int = Field(description="创建时间(秒)")
    user_name: str = Field(
        sa_column=Column(String(30), nullable=False), description="用户名称"
    )
    user_id: int = Field(
        sa_column=Column(BigInteger, nullable=False), description="用户ID"
    )
    gong_id: int = Field(default=0, description="供应商ID")
    goods_id: int = Field(
        sa_column=Column(Integer, nullable=False), description="商品ID"
    )
    admin_id: int = Field(default=0, description="分站站长ID")
    goods_name: str = Field(
        sa_column=Column(String(120), nullable=False), description="商品名称"
    )
    shequ_id: int = Field(default=0, description="社区ID")
    order_s_n: str = Field(
        sa_column=Column(String(100), nullable=False), description="自己的订单编号"
    )
    other_order_s_n: Optional[str] = Field(
        default="0",
        sa_column=Column(String(250), nullable=True),
        description="三方的订单号",
    )
    dj_status: int = Field(default=0, description="对接状态 0:未对接 1:成功 2:失败")
    order_status: int = Field(
        default=0,
        description="-1:待付款,1:已付款,2:处理中,3:异常,4:已完成,5:退单中,6:已退单,7:已退款,8:待处理",
    )
    refund_number: int = Field(default=0, description="退款数量")
    refund_amount: Decimal = Field(
        default=Decimal("0.00000000"),
        sa_column=Column(Numeric(15, 8), nullable=False, default=Decimal("0")),
        description="退款金额",
    )
    order_num: int = Field(description="订单数量")
    current_num: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, default=0),
        description="当前数量",
    )
    start_num: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, default=0),
        description="初始数量",
    )
    order_amount: Decimal = Field(
        default=Decimal("0.00000000"),
        sa_column=Column(Numeric(15, 8), nullable=False, default=Decimal("0")),
        description="总价",
    )
    price: Decimal = Field(
        default=Decimal("0.00000000"),
        sa_column=Column(Numeric(15, 8), nullable=False, default=Decimal("0")),
        description="商品单价",
    )
    order_remark: Optional[str] = Field(
        default=None,
        sa_column=Column(String(500), nullable=True),
        description="订单备注",
    )
    params: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="下单参数(JSON)",
    )
    back_time: Optional[int] = Field(default=None, description="退款时间(秒)")
    cost: Decimal = Field(
        default=Decimal("0.00000000"),
        sa_column=Column(Numeric(15, 8), nullable=False, default=Decimal("0")),
        description="商品成本价",
    )
    complete_time: Optional[int] = Field(default=None, description="完成时间(秒)")
    logs: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="订单操作记录(JSON)",
    )
    card_number: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="卡密(多条用逗号分隔)",
    )
    remarks: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
        description="操作备注",
    )
    s_name: Optional[str] = Field(
        default=None,
        sa_column=Column(String(120), nullable=True),
        description="社区名称",
    )
    zx_type: int = Field(
        default=1, description="执行类型:1立即 2定时 3结束后延迟 4每天"
    )
    zx_order_id: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, default=0),
        description="关联完成后计算执行时间的订单ID",
    )
    img: Optional[str] = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
        description="商品图片",
    )
    tb_time: int = Field(default=0, description="最近同步时间")
    ip: Optional[str] = Field(
        default=None,
        sa_column=Column("Ip", String(255), nullable=True),
        description="下单IP",
    )
    goods_type: int = Field(default=1, description="1正常 2卡密商品")

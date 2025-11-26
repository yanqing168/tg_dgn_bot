"""
TRXNO/TRXFAST API 客户端
对接能量购买API
"""
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from .models import (
    APIAccountInfo,
    APIPriceQuery,
    APIOrderResponse,
    EnergyPackage,
)


class EnergyAPIError(Exception):
    """API错误"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API Error {code}: {message}")


class EnergyAPIClient:
    """能量API客户端"""
    
    # API状态码
    CODE_SUCCESS = 10000
    CODE_PARAM_ERROR = 10001
    CODE_INSUFFICIENT_BALANCE = 10002
    CODE_AUTH_ERROR = 10003
    CODE_ORDER_NOT_FOUND = 10004
    CODE_ACTIVATION_FAILED = 10005
    CODE_ADDRESS_NOT_ACTIVATED = 10009
    CODE_SERVER_ERROR = 10010
    CODE_PACKAGE_EXISTS = 10011
    
    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://trxno.com",
        backup_url: str = "https://trxfast.com",
        timeout: float = 30.0
    ):
        """
        初始化API客户端
        
        Args:
            username: API用户名
            password: API密码
            base_url: 主URL
            backup_url: 备用URL
            timeout: 超时时间(秒)
        """
        self.username = username
        self.password = password
        self.base_url = base_url
        self.backup_url = backup_url
        self.timeout = timeout
        
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    async def _request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        use_backup: bool = False
    ) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            data: 请求数据
            use_backup: 是否使用备用URL
        
        Returns:
            API响应数据
        
        Raises:
            EnergyAPIError: API错误
            httpx.HTTPError: HTTP错误
        """
        url = f"{self.backup_url if use_backup else self.base_url}{endpoint}"
        
        # 添加认证信息
        request_data = {
            "username": self.username,
            "password": self.password,
            **data
        }
        
        try:
            # M2 安全加固：只记录端点，不打印完整请求数据
            logger.info(f"API请求: {endpoint}")
            
            response = await self._client.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            # M2 安全加固：只记录状态码，不打印完整响应
            logger.info(f"API响应: code={result.get('code')}, msg={result.get('msg', '')}")
            
            # 检查状态码
            code = result.get("code")
            if code != self.CODE_SUCCESS:
                msg = result.get("msg", "未知错误")
                logger.warning(f"API业务错误: code={code}, msg={msg}")
                raise EnergyAPIError(code, msg)
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP错误: {e}")
            # 如果主URL失败且未使用备用URL，尝试备用URL
            if not use_backup:
                logger.info("尝试使用备用URL")
                return await self._request(endpoint, data, use_backup=True)
            raise
    
    async def get_account_info(self) -> APIAccountInfo:
        """
        查询账号信息
        
        Returns:
            账号信息
        """
        result = await self._request("/api/account", {})
        data = result.get("data", {})
        
        return APIAccountInfo(
            username=data.get("username", self.username),
            balance_trx=float(data.get("balance", 0)),
            balance_usdt=float(data.get("balance_usdt", 0)),
            frozen_balance=float(data.get("frozen_balance", 0))
        )
    
    async def query_price(self) -> APIPriceQuery:
        """
        查询当前价格
        
        Returns:
            价格信息
        """
        result = await self._request("/api/price", {})
        data = result.get("data", {})
        
        return APIPriceQuery(
            energy_65k_price=float(data.get("energy_65k", 3.0)),
            energy_131k_price=float(data.get("energy_131k", 6.0)),
            package_price=float(data.get("package_price", 3.6))
        )
    
    async def buy_energy(
        self,
        receive_address: str,
        energy_amount: int,
        rent_time: int = 1
    ) -> APIOrderResponse:
        """
        为指定地址购买时长能量
        
        Args:
            receive_address: 接收地址
            energy_amount: 能量数量(65000或131000)
            rent_time: 租用时长(小时)，当前仅支持1
        
        Returns:
            订单响应
        """
        data = {
            "re_type": "ENERGY",
            "re_address": receive_address,
            "re_value": energy_amount,
            "rent_time": rent_time
        }
        
        result = await self._request("/api/buyenergy", data)
        
        return APIOrderResponse(
            code=result.get("code"),
            msg=result.get("msg"),
            data=result.get("data"),
            order_id=result.get("data", {}).get("order_id")
        )
    
    async def auto_buy_energy(
        self,
        receive_address: str,
        transfer_trx: float
    ) -> APIOrderResponse:
        """
        自动计算并购买能量
        根据转入的TRX金额自动计算能量数量
        
        Args:
            receive_address: 接收地址
            transfer_trx: 转入的TRX金额
        
        Returns:
            订单响应
        """
        data = {
            "re_address": receive_address,
            "transfer_trx": transfer_trx
        }
        
        result = await self._request("/api/autobuyenergy", data)
        
        return APIOrderResponse(
            code=result.get("code"),
            msg=result.get("msg"),
            data=result.get("data"),
            order_id=result.get("data", {}).get("order_id")
        )
    
    async def recycle_energy(self, order_id: str) -> APIOrderResponse:
        """
        主动提前回收时长能量
        
        Args:
            order_id: 订单ID
        
        Returns:
            回收响应
        """
        data = {"order_id": order_id}
        
        result = await self._request("/api/recycleenergy", data)
        
        return APIOrderResponse(
            code=result.get("code"),
            msg=result.get("msg"),
            data=result.get("data")
        )
    
    async def buy_package(
        self,
        receive_address: str
    ) -> APIOrderResponse:
        """
        购买笔数能量套餐
        
        Args:
            receive_address: 接收地址
        
        Returns:
            订单响应
        """
        data = {"re_address": receive_address}
        
        result = await self._request("/api/buypackage", data)
        
        return APIOrderResponse(
            code=result.get("code"),
            msg=result.get("msg"),
            data=result.get("data"),
            order_id=result.get("data", {}).get("order_id")
        )
    
    async def activate_address(
        self,
        target_address: str
    ) -> APIOrderResponse:
        """
        激活地址
        
        Args:
            target_address: 要激活的地址
        
        Returns:
            激活响应
        """
        data = {"target_address": target_address}
        
        result = await self._request("/api/activate", data)
        
        return APIOrderResponse(
            code=result.get("code"),
            msg=result.get("msg"),
            data=result.get("data")
        )
    
    async def query_order(self, order_id: str) -> APIOrderResponse:
        """
        查询订单状态
        
        Args:
            order_id: 订单ID
        
        Returns:
            订单信息
        """
        data = {"order_id": order_id}
        
        result = await self._request("/api/order", data)
        
        return APIOrderResponse(
            code=result.get("code"),
            msg=result.get("msg"),
            data=result.get("data")
        )
    
    async def query_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        查询账号日志
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            page: 页码
            page_size: 每页数量
        
        Returns:
            日志数据
        """
        data = {
            "page": page,
            "page_size": page_size
        }
        
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date
        
        result = await self._request("/api/logs", data)
        
        return result.get("data", {})

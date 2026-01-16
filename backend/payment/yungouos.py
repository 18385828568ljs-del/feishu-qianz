"""
YunGouOS 支付宝支付服务
文档：https://open.pay.yungouos.com

支持的支付方式：
- 扫码支付 (Native) - 生成二维码
- H5支付 - 移动端唤起支付宝
"""
import hashlib
import time
import uuid
import requests
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class YunGouOSPayment:
    """YunGouOS 支付宝支付服务"""
    
    BASE_URL = "https://api.pay.yungouos.com"
    
    def __init__(self):
        self.mch_id = os.getenv("YUNGOUOS_MCH_ID", "")
        self.key = os.getenv("YUNGOUOS_KEY", "")
        self.notify_url = os.getenv("YUNGOUOS_NOTIFY_URL", "")
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成签名
        
        签名规则：
        1. 将参数按照 ASCII 码从小到大排序
        2. 拼接成 key=value&key2=value2 格式
        3. 在末尾拼接 &key=商户密钥
        4. 进行 MD5 加密并转大写
        """
        # 过滤空值和 sign 字段
        filtered_params = {k: v for k, v in params.items() if v is not None and v != "" and k != "sign"}
        
        # 按 ASCII 码排序
        sorted_keys = sorted(filtered_params.keys())
        
        # 拼接字符串
        sign_str = "&".join([f"{k}={filtered_params[k]}" for k in sorted_keys])
        
        # 追加密钥
        sign_str += f"&key={self.key}"
        
        # MD5 加密并转大写
        sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
        
        return sign
    
    def _verify_sign(self, params: Dict[str, Any]) -> bool:
        """验证回调签名"""
        if "sign" not in params:
            return False
        
        received_sign = params["sign"]
        calculated_sign = self._generate_sign(params)
        
        return received_sign == calculated_sign
    
    def native_pay(
        self,
        out_trade_no: str,
        total_fee: float,
        body: str,
        attach: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        支付宝扫码支付（Native）
        
        Args:
            out_trade_no: 商户订单号
            total_fee: 支付金额（元）
            body: 商品描述
            attach: 附加数据，回调时原样返回
            
        Returns:
            {
                "success": bool,
                "qr_code": str,  # 二维码图片URL或二维码内容
                "order_no": str,  # 系统订单号
                "error": str  # 错误信息（失败时）
            }
        """
        url = f"{self.BASE_URL}/api/pay/alipay/nativePay"
        
        params = {
            "out_trade_no": out_trade_no,
            "total_fee": str(total_fee),
            "mch_id": self.mch_id,
            "body": body,
            "attach": attach or "",
            "notify_url": self.notify_url,
        }
        
        params["sign"] = self._generate_sign(params)
        
        try:
            response = requests.post(url, data=params, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                return {
                    "success": True,
                    "qr_code": result.get("data"),  # 二维码链接
                    "order_no": out_trade_no,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "支付创建失败"),
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"请求失败: {str(e)}",
            }
    
    def h5_pay(
        self,
        out_trade_no: str,
        total_fee: float,
        body: str,
        attach: Optional[str] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        支付宝 H5 支付
        
        Args:
            out_trade_no: 商户订单号
            total_fee: 支付金额（元）
            body: 商品描述
            attach: 附加数据
            return_url: 支付完成后跳转地址
            
        Returns:
            {
                "success": bool,
                "pay_url": str,  # 跳转支付URL
                "order_no": str,
                "error": str
            }
        """
        url = f"{self.BASE_URL}/api/pay/alipay/h5Pay"
        
        params = {
            "out_trade_no": out_trade_no,
            "total_fee": str(total_fee),
            "mch_id": self.mch_id,
            "body": body,
            "attach": attach or "",
            "notify_url": self.notify_url,
        }
        
        if return_url:
            params["return_url"] = return_url
        
        params["sign"] = self._generate_sign(params)
        
        try:
            response = requests.post(url, data=params, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                return {
                    "success": True,
                    "pay_url": result.get("data"),  # 跳转链接
                    "order_no": out_trade_no,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "支付创建失败"),
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"请求失败: {str(e)}",
            }
    
    def query_order(self, out_trade_no: str) -> Dict[str, Any]:
        """
        查询订单状态
        
        Args:
            out_trade_no: 商户订单号
            
        Returns:
            {
                "success": bool,
                "trade_state": str,  # NOTPAY/SUCCESS/REFUND
                "trade_no": str,  # 支付宝交易号
                "error": str
            }
        """
        url = f"{self.BASE_URL}/api/pay/alipay/getPayResult"
        
        params = {
            "out_trade_no": out_trade_no,
            "mch_id": self.mch_id,
        }
        
        params["sign"] = self._generate_sign(params)
        
        try:
            response = requests.get(url, params=params, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                data = result.get("data", {})
                return {
                    "success": True,
                    "trade_state": data.get("trade_state", "NOTPAY"),
                    "trade_no": data.get("trade_no"),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "查询失败"),
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"请求失败: {str(e)}",
            }
    
    def handle_notify(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理支付回调通知
        
        Args:
            params: 回调参数
            
        Returns:
            {
                "success": bool,
                "out_trade_no": str,  # 商户订单号
                "total_fee": str,  # 支付金额
                "attach": str,  # 附加数据
                "trade_no": str,  # 支付宝交易号
                "error": str
            }
        """
        # 验证签名
        if not self._verify_sign(params):
            return {
                "success": False,
                "error": "签名验证失败",
            }
        
        # 验证商户号
        if params.get("mchId") != self.mch_id:
            return {
                "success": False,
                "error": "商户号不匹配",
            }
        
        return {
            "success": True,
            "out_trade_no": params.get("outTradeNo"),
            "total_fee": params.get("payMoney"),
            "attach": params.get("attach"),
            "trade_no": params.get("payNo"),
        }
    
    @staticmethod
    def generate_order_no() -> str:
        """生成唯一订单号"""
        timestamp = int(time.time() * 1000)
        random_str = uuid.uuid4().hex[:6].upper()
        return f"ALI{timestamp}{random_str}"


# 创建全局单例
yungouos_payment = YunGouOSPayment()

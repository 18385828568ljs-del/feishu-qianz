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
import base64
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
    
    def _generate_sign(self, params: Dict[str, Any], mandatory_keys: Optional[list] = None) -> str:
        """
        生成签名
        
        签名规则：
        1. 过滤文档中标记为“必填”的参数
        2. 将参数按照 ASCII 码从小到大排序
        3. 拼接成 key=value&key2=value2 格式
        4. 在末尾拼接 &key=商户密钥
        5. 进行 MD5 加密并转大写
        """
        # 官方规则：只有文档中的必填参数才参与签名！！！
        if mandatory_keys:
            filtered_params = {k: str(v) for k, v in params.items() if k in mandatory_keys and v is not None and v != ""}
        else:
            # 兼容模式：过滤空值和 sign 字段
            filtered_params = {k: str(v) for k, v in params.items() if v is not None and v != "" and k != "sign"}
        
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
        # 回调通知中的参数参与签名规则可能不同，通常全量参与
        calculated_sign = self._generate_sign(params)
        
        return received_sign == calculated_sign
    
    def native_pay(
        self,
        out_trade_no: str,
        total_fee: float,
        body: str,
        attach: Optional[str] = None
    ) -> Dict[str, Any]:
        """支付宝扫码支付（Native）"""
        import logging
        logger = logging.getLogger("uvicorn.error")
        
        url = f"{self.BASE_URL}/api/pay/alipay/nativePay"
        
        # 确保金额格式为两位小数的字符串
        formatted_fee = "{:.2f}".format(total_fee)
        
        params = {
            "out_trade_no": out_trade_no,
            "total_fee": formatted_fee,
            "mch_id": self.mch_id,
            "body": body,
            "attach": attach or "",
            "notify_url": self.notify_url,
            "type": "2",  # 告知云沟直接返回二维码图片链接，而不是 HTML 页面
        }
        
        # 官方规则：Native 支付参与签名的只有这四个必填项
        mandatory_keys = ["out_trade_no", "total_fee", "mch_id", "body"]
        params["sign"] = self._generate_sign(params, mandatory_keys)
        
        logger.info(f"Connecting to YunGouOS Native: {url} with params: {params}")
        
        try:
            response = requests.post(url, data=params, timeout=30)
            result = response.json()
            logger.info(f"YunGouOS Native Response: {result}")
            
            if result.get("code") == 0:
                qr_url = result.get("data")
                # 核心修复：后端代理下载图片并转为 Base64
                # 这样可以解决飞书安全域名限制和 HTTP/HTTPS 协议冲突问题
                try:
                    img_resp = requests.get(qr_url, timeout=10)
                    if img_resp.status_code == 200:
                        base64_data = base64.b64encode(img_resp.content).decode('utf-8')
                        # 返回完整的 Data URI 格式
                        qr_code_base64 = f"data:image/png;base64,{base64_data}"
                        return {
                            "success": True,
                            "qr_code": qr_code_base64,
                            "order_no": out_trade_no,
                        }
                    else:
                        logger.error(f"Failed to download QR code image: {img_resp.status_code}")
                except Exception as img_err:
                    logger.error(f"Failed to convert QR code to base64: {str(img_err)}")
                
                # 如果转换失败，退回到原始 URL
                return {
                    "success": True,
                    "qr_code": qr_url,
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
        """支付宝 H5 支付"""
        import logging
        logger = logging.getLogger("uvicorn.error")
        
        url = f"{self.BASE_URL}/api/pay/alipay/h5Pay"
        
        # 确保金额格式为两位小数的字符串
        formatted_fee = "{:.2f}".format(total_fee)
        
        params = {
            "out_trade_no": out_trade_no,
            "total_fee": formatted_fee,
            "mch_id": self.mch_id,
            "body": body,
            "attach": attach or "",
            "notify_url": self.notify_url,
        }
        
        if return_url:
            params["return_url"] = return_url
        
        # 官方规则：H5 支付参与签名的同样只有这四个必填项
        mandatory_keys = ["out_trade_no", "total_fee", "mch_id", "body"]
        params["sign"] = self._generate_sign(params, mandatory_keys)
        
        logger.info(f"Connecting to YunGouOS H5: {url} with params: {params}")
        
        try:
            response = requests.post(url, data=params, timeout=30)
            result = response.json()
            logger.info(f"YunGouOS H5 Response: {result}")
            
            if result.get("code") == 0:
                return {
                    "success": True,
                    "pay_url": result.get("data"),
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
        """查询订单状态"""
        url = f"{self.BASE_URL}/api/system/order/getPayOrderInfo"
        
        params = {
            "out_trade_no": out_trade_no,
            "mch_id": self.mch_id,
        }
        
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.info(f"Querying order {out_trade_no} from YunGouOS...")
        
        mandatory_keys = ["out_trade_no", "mch_id"]
        params["sign"] = self._generate_sign(params, mandatory_keys)
        
        logger.info(f"Query parameters: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            result = response.json()
            logger.info(f"YunGouOS Query Response: {result}")
            
            if result.get("code") == 0:
                data = result.get("data", {})
                # 新接口返回字段不同：payStatus 0=未支付 1=已支付
                pay_status = data.get("payStatus", 0)
                is_paid = str(pay_status) == "1"
                
                return {
                    "success": True,
                    "trade_state": "SUCCESS" if is_paid else "NOTPAY",
                    "trade_no": data.get("payNo"),  # 支付宝/微信的交易号通常在 payNo
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
        """处理支付回调通知"""
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.info(f"Received YunGouOS Notify: {params}")
        
        # 验证签名
        if not self._verify_sign(params):
            logger.warning(f"YunGouOS Notify Signature Mismatch!")
            # 记录一下我们自己生成的签名和收到的签名
            received_sign = params.get("sign")
            calculated_sign = self._generate_sign(params)
            logger.debug(f"Received: {received_sign}, Calculated: {calculated_sign}")
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
        return f"ORD-{time.strftime('%Y%m%d%H%M%S')}-{random_str}"


# 创建全局单例
yungouos_payment = YunGouOSPayment()

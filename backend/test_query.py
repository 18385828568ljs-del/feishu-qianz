import hashlib
import requests
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class TestYunGouOS:
    def __init__(self):
        self.mch_id = os.getenv("YUNGOUOS_MCH_ID")
        self.key = os.getenv("YUNGOUOS_KEY")
        self.base_url = "https://api.pay.yungouos.com"
        
        print(f"Loaded config: MCH_ID={self.mch_id}, KEY={self.key[:4]}***")

    def _generate_sign(self, params, mandatory_keys=None):
        if mandatory_keys:
            filtered_params = {k: str(v) for k, v in params.items() if k in mandatory_keys and v is not None}
        else:
            filtered_params = {k: str(v) for k, v in params.items() if v is not None and v != "" and k != "sign"}
        
        sorted_keys = sorted(filtered_params.keys())
        sign_str = "&".join([f"{k}={filtered_params[k]}" for k in sorted_keys])
        sign_str += f"&key={self.key}"
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    def query_order(self, out_trade_no):
        # 切换到系统通用查询接口
        url = f"{self.base_url}/api/system/order/getPayOrderInfo"
        
        params = {
            "out_trade_no": out_trade_no,
            "mch_id": self.mch_id,
        }
        
        # 必填项参与签名
        mandatory_keys = ["out_trade_no", "mch_id"]
        params["sign"] = self._generate_sign(params, mandatory_keys)
        
        print(f"\n--- Request ---")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            result = response.json()
            print(f"\n--- Response ---")
            print(result)
            return result
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    tester = TestYunGouOS()
    # 填入刚才失败的那个订单号，或者一个新的待测订单号
    # 用户可以在运行前修改这里，或者我们留一个 input
    order_id = input("请输入要查询的订单号 (直接回车默认使用 ORD-20260116103936-F6AACB): ").strip()
    if not order_id:
        order_id = "ORD-20260116103936-F6AACB"
    
    tester.query_order(order_id)

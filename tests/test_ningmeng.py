import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ningmeng import NingMengAPI
from config import CONFIG


class TestNingMengAPI(unittest.TestCase):
    def setUp(self):
        self.api = NingMengAPI(str(CONFIG["NINGMENG_USERNAME"]), str(CONFIG["NINGMENG_PASSWORD"]))
        self.api.login()

    def test_login(self):
        print("Session ID after login:", self.api.cookies["session_id"])
        self.assertNotEqual(self.api.cookies["session_id"], "")

    def test_query_order(self):
        order_sn = "1007019"  # 替换为一个有效的订单号进行测试
        order_info = self.api.query_order(order_sn)
        self.assertIsInstance(order_info, dict)
        self.assertEqual(order_info.get("receive_order"), order_sn)
        
        
if __name__ == '__main__':
    unittest.main()
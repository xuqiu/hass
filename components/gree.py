"""
文件名：gree.py.
格力云控的控件,通过逆向gree+ 模拟app控制格力中央空调
"""

DOMAIN = "gree"
def setup(hass, config):
    attr = {"icon": "mdi:air-conditioner",
            "friendly_name": "格力空调",
            "slogon": "欢迎使用格力云控！"}
    hass.states.set(DOMAIN+".hello_world", "太棒了！", attributes=attr)
    return True
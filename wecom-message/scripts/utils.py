import os
import json
import sys
import urllib.request

# 脚本相对路径定位 config.json
# Script relative path to locate config.json
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "../config.json")

def load_config():
    """加载配置文件 / Load configuration file"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: 加载 config.json 失败: {e}", file=sys.stderr)
    return {}

def get_access_token(corpid=None, corpsecret=None):
    """获取企业微信 access_token / Get WeCom access_token"""
    if not corpid or not corpsecret:
        config = load_config()
        corpid = corpid or config.get("corpid")
        corpsecret = corpsecret or config.get("corpsecret")
    
    if not corpid or not corpsecret:
        print("Error: 未提供 corpid 或 corpsecret", file=sys.stderr)
        return None

    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get("errcode", -1) == 0:
            return data["access_token"]
        else:
            print(f"Error: 获取 token 失败: {data.get('errmsg')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error: 请求 token 异常: {e}", file=sys.stderr)
        return None

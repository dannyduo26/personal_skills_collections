#!/usr/bin/env python3
# 企业微信消息接收验证服务器
# 用途：在企业微信后台配置"接收消息服务器" URL 验证时使用
# 文档：https://developer.work.weixin.qq.com/document/path/90238

import hashlib
import base64
import struct
import sys
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from xml.etree import ElementTree as ET
from utils import load_config

try:
    from Crypto.Cipher import AES
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Remove local definition of load_config as it is now in utils.py


def verify_signature(token, timestamp, nonce, echostr_encrypted, msg_signature):
    """
    验证企业微信消息签名
    排序规则：将 token/timestamp/nonce/echostr_encrypted 拼接后 SHA1
    """
    parts = sorted([token, timestamp, nonce, echostr_encrypted])
    sha1 = hashlib.sha1("".join(parts).encode('utf-8')).hexdigest()
    return sha1 == msg_signature


def decrypt_echostr(encoding_aes_key, echostr_encrypted, corp_id):
    """
    解密企业微信 echostr（AES-256-CBC，需要 pycryptodome）
    返回解密后的明文字节
    """
    if not HAS_CRYPTO:
        raise RuntimeError("需要安装 pycryptodome：pip install pycryptodome")

    # EncodingAESKey base64 解码得到 32 字节 AES Key
    aes_key = base64.b64decode(encoding_aes_key + "=")
    # 解密
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
    plain = cipher.decrypt(base64.b64decode(echostr_encrypted))
    # 去除 PKCS7 padding
    pad_len = plain[-1]
    plain = plain[:-pad_len]
    # 结构：16字节随机串 + 4字节消息长度 + 消息内容 + corp_id
    content_len = struct.unpack(">I", plain[16:20])[0]
    content = plain[20:20 + content_len]
    from_corp_id = plain[20 + content_len:].decode('utf-8')
    if from_corp_id != corp_id:
        raise ValueError(f"corp_id 不匹配: expected={corp_id}, got={from_corp_id}")
    return content


class WeChatHandler(BaseHTTPRequestHandler):
    """处理企业微信回调请求"""

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{self.log_date_time_string()}] {format % args}")

    def do_GET(self):
        """处理 GET 请求：企业微信服务器 URL 验证"""
        config = load_config()
        token = config.get("callback_token", "")
        encoding_aes_key = config.get("encoding_aes_key", "")
        corp_id = config.get("corpid", "")

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        msg_signature = params.get("msg_signature", [""])[0]
        timestamp     = params.get("timestamp", [""])[0]
        nonce         = params.get("nonce", [""])[0]
        echostr       = params.get("echostr", [""])[0]

        print(f"收到验证请求: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}")

        # 验证签名
        if not verify_signature(token, timestamp, nonce, echostr, msg_signature):
            print("Error: 签名验证失败")
            self.send_response(403)
            self.end_headers()
            return

        # 解密 echostr
        try:
            plain = decrypt_echostr(encoding_aes_key, echostr, corp_id)
            print(f"验证成功，返回 echostr: {plain}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(plain)
        except Exception as e:
            print(f"Error: 解密失败: {e}")
            self.send_response(500)
            self.end_headers()

    def do_POST(self):
        """处理 POST 请求：接收企业微信推送消息（打印原始内容）"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        print(f"收到推送消息:\n{body.decode('utf-8', errors='replace')}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"success")


def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="企业微信消息接收验证服务器")
    parser.add_argument("--port", type=int, default=8088, help="监听端口（默认 8088）")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    args = parser.parse_args()

    # 检查 pycryptodome
    if not HAS_CRYPTO:
        print("警告: 未安装 pycryptodome，签名验证将正常，但 echostr 解密会失败。")
        print("      请运行: pip install pycryptodome")

    server = HTTPServer((args.host, args.port), WeChatHandler)
    local_ip = get_local_ip()
    print(f"服务器已启动，监听 {args.host}:{args.port}")
    print(f"本机 IP: {local_ip}:{args.port}")
    print(f"企业微信后台填写 URL 时请使用公网 IP 或域名，例如：")
    print(f"  http://<公网IP或域名>:{args.port}/wecom/callback")
    print("按 Ctrl+C 停止服务器")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")

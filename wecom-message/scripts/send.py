#!/usr/bin/env python3
# 企业微信应用消息发送脚本（支持文本、Markdown、图片）
import argparse
import urllib.request
import urllib.parse
import json
import sys
import mimetypes
import uuid
import os
from utils import load_config, get_access_token

# Windows 终端默认 GBK 编码，强制改为 UTF-8 以支持 emoji 等字符
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr.reconfigure(encoding='utf-8')

# Remove local definitions of load_config and get_access_token as they are now in utils.py


def upload_image(token, image_path):
    """
    上传本地图片到企业微信临时素材，返回 media_id
    支持格式：jpg、png、gif、bmp（大小限制 10MB）
    """
    if not os.path.isfile(image_path):
        print(f"Error: 图片文件不存在: {image_path}", file=sys.stderr)
        return None

    url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type=image"
    mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    filename = os.path.basename(image_path)

    # 手动构造 multipart/form-data
    boundary = uuid.uuid4().hex
    try:
        with open(image_path, 'rb') as f:
            file_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode('utf-8') + file_data + f"\r\n--{boundary}--\r\n".encode('utf-8')

        req = urllib.request.Request(url, data=body, method='POST',
                                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        
        if result.get("media_id"):
            print(f"图片上传临时素材成功: media_id={result['media_id']}")
            return result["media_id"]
        else:
            print(f"Error: 图片上传失败: {result.get('errmsg')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error: 上传请求异常: {e}", file=sys.stderr)
        return None


def upload_permanent_image(token, image_path):
    """
    上传本地图片到企业微信，得到一个永久 URL
    此 URL 可在 Markdown 消息中显示。
    """
    if not os.path.isfile(image_path):
        print(f"Error: 图片文件不存在: {image_path}", file=sys.stderr)
        return None

    url = f"https://qyapi.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
    mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    filename = os.path.basename(image_path)

    # 手动构造 multipart/form-data
    boundary = uuid.uuid4().hex
    try:
        with open(image_path, 'rb') as f:
            file_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode('utf-8') + file_data + f"\r\n--{boundary}--\r\n".encode('utf-8')

        req = urllib.request.Request(url, data=body, method='POST',
                                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        
        if result.get("url"):
            print(f"图片永久上传成功: {result['url']}")
            return result["url"]
        else:
            print(f"Error: 永久图片上传失败: {result.get('errmsg')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error: 永久上传请求异常: {e}", file=sys.stderr)
        return None


def send_message(corpid, corpsecret, agentid, touser, title, body, msgtype="text", image_path=None):
    """
    发送企业微信应用消息
    各消息类型及限制：
    - text: 纯文本。标题和正文合并，最长 2048 字节 (约 600-700 汉字)。
    - markdown: Markdown 格式。最长 2048 字节。
    - image: 图片。需提供 image_path，上传临时素材 (限制 10MB)。
    - news: 图文。点击跳转外部 URL。描述 (body) 限制 512 字节，超过截断。
    - mpnews: 图文 (含正文)。在企业微信内打开。正文 (body) 极长 (支持 HTML，上限 666KB)，封面图需 10MB 以内。
    - template_card: 模板卡片。标题 128 字符，内容列表最多 4 项。
    """
    token = get_access_token(corpid, corpsecret)
    if not token:
        return False

    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

    if msgtype == "image":
        # 上传临时素材获取 media_id
        if not image_path:
            print("Error: 发送图片消息需要提供 --image 参数", file=sys.stderr)
            return False
        media_id = upload_image(token, image_path)
        if not media_id:
            return False
        payload = {
            "touser": touser,
            "msgtype": "image",
            "agentid": int(agentid),
            "image": {"media_id": media_id},
            "safe": 0
        }
    elif msgtype == "news":
        # 图文消息：上传图片获取永久 URL 作为 picurl，body 为文章描述
        if not image_path:
            print("Error: 发送图文消息需要提供 --image 参数", file=sys.stderr)
            return False
        picurl = upload_permanent_image(token, image_path)
        if not picurl:
            return False
        payload = {
            "touser": touser,
            "msgtype": "news",
            "agentid": int(agentid),
            "news": {
                "articles": [{
                    "title": title,
                    "description": body,
                    "picurl": picurl
                }]
            }
        }
    elif msgtype == "mpnews":
        # 图文消息（含正文）：上传图片作为封面图，同时上传为永久 URL 嵌入正文
        if not image_path:
            print("Error: 发送 mpnews 消息需要提供 --image 参数作为封面图", file=sys.stderr)
            return False
        
        # 1. 上传临时素材作为卡片封面 (media_id)
        media_id = upload_image(token, image_path)
        if not media_id:
            return False
        
        # 2. 上传永久图片作为正文插图 (url)
        pic_url = upload_permanent_image(token, image_path)
        
        # 构造正文：支持 {{IMAGE}} 占位符自定义位置，若无占位符则默认置顶
        content = body if body else title
        if pic_url:
            img_tag = f'<img src="{pic_url}" />'
            if "{{IMAGE}}" in content:
                content = content.replace("{{IMAGE}}", img_tag)
            else:
                content = f'{img_tag}<br/>' + content

        payload = {
            "touser": touser,
            "msgtype": "mpnews",
            "agentid": int(agentid),
            "mpnews": {
                "articles": [{
                    "title": title,
                    "thumb_media_id": media_id,
                    "author": "System",
                    "content": content,
                    "digest": body[:512] if body else title,
                    "content_source_url": ""
                }]
            }
        }
    elif msgtype == "template_card":
        # 模板卡片消息
        lines = [line.strip() for line in body.split('\n') if line.strip()]
        # 企业微信限制 vertical_content_list 最多 4 个，每项必须有 title
        content_items = [{"title": line[:256]} for line in lines[:4]]
        if not content_items:
            content_items = [{"title": "详情请见内容"}]
        
        if image_path:
            # 有图片则使用 news_notice
            picurl = upload_permanent_image(token, image_path)
            if not picurl:
                return False
            payload = {
                "touser": touser,
                "msgtype": "template_card",
                "agentid": int(agentid),
                "template_card": {
                    "card_type": "news_notice",
                    "source": {
                        "desc": "系统通知"
                    },
                    "main_title": {
                        "title": title[:128]
                    },
                    "card_image": {
                        "url": picurl,
                        "aspect_ratio": 2.25
                    },
                    "vertical_content_list": content_items,
                    "card_action": {
                        "type": 1,
                        "url": "https://work.weixin.qq.com"
                    }
                }
            }
        else:
            # 无图片则使用 text_notice
            payload = {
                "touser": touser,
                "msgtype": "template_card",
                "agentid": int(agentid),
                "template_card": {
                    "card_type": "text_notice",
                    "source": {
                        "desc": "文字通知"
                    },
                    "main_title": {
                        "title": title[:128]
                    },
                    "vertical_content_list": content_items,
                    "card_action": {
                        "type": 1,
                        "url": "https://work.weixin.qq.com"
                    }
                }
            }
    else:
        # 构造纯文本/Markdown 内容
        full_content = f"{title}\n{body}" if body else title
        if msgtype == "text":
            payload = {
                "touser": touser,
                "msgtype": "text",
                "agentid": int(agentid),
                "text": {"content": full_content},
                "safe": 0
            }
        elif msgtype == "markdown":
            payload = {
                "touser": touser,
                "msgtype": "markdown",
                "agentid": int(agentid),
                "markdown": {"content": full_content},
            }
        else:
            print(f"Error: 不支持的消息类型: {msgtype}", file=sys.stderr)
            return False
    # 发送请求
    encoded = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=encoded, method='POST',
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        if result.get("errcode") == 0:
            print(f"消息发送成功: {title or '图片'}")
            return True
        else:
            print(f"Error: 消息发送失败: {result.get('errmsg')}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error: 发送请求异常: {e}", file=sys.stderr)
        return False


def get_callback_ips(corpid, corpsecret):
    """
    获取企业微信服务器的回调 IP 段
    文档：https://developer.work.weixin.qq.com/document/path/90237
    """
    token = get_access_token(corpid, corpsecret)
    if not token:
        return False

    url = f"https://qyapi.weixin.qq.com/cgi-bin/getcallbackip?access_token={token}"
    try:
        with urllib.request.urlopen(url) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        if result.get("errcode", -1) == 0:
            print("企业微信回调 IP 段：")
            print(json.dumps(result.get("ip_list", []), indent=2))
            return True
        else:
            print(f"Error: 获取 IP 段失败: {result.get('errmsg')}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error: 请求 IP 段异常: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    config = load_config()

    parser = argparse.ArgumentParser(description="企业微信应用消息发送及工具脚本")
    parser.add_argument("--corpid",    default=config.get("corpid"),    help="企业 ID")
    parser.add_argument("--corpsecret",default=config.get("corpsecret"),help="应用 Secret")
    parser.add_argument("--agentid",   default=config.get("agentid"),   help="应用 AgentID")
    parser.add_argument("--touser",    default=config.get("touser", "@all"), help="收件人，多个用 | 分隔")
    parser.add_argument("--title",     default="",                      help="消息标题/主内容（image/get-ips 类型可省略）")
    parser.add_argument("--body",      default="",                      help="消息正文（可选）")
    parser.add_argument("--msgtype",   default="text", choices=["text", "markdown", "image", "news", "mpnews", "template_card"], help="消息类型")
    parser.add_argument("--image",     default=None,                    help="本地图片路径 (msgtype=image/news/template_card 时必填)")
    parser.add_argument("--get-ips",   action="store_true",             help="获取企业微信回调 IP 段")

    args = parser.parse_args()

    # 检查必填参数
    if not args.corpid or not args.corpsecret:
        print("Error: 请在 config.json 或命令行中提供 corpid 和 corpsecret", file=sys.stderr)
        sys.exit(1)

    # 优先处理工具类指令
    if args.get_ips:
        success = get_callback_ips(args.corpid, args.corpsecret)
        sys.exit(0 if success else 1)

    # 消息发送相关的参数检查
    if not args.agentid:
        print("Error: 发送消息请提供 agentid", file=sys.stderr)
        sys.exit(1)
    if args.msgtype not in ("image", "news", "template_card") and not args.title:
        print("Error: text/markdown/template_card 消息需要提供 --title", file=sys.stderr)
        sys.exit(1)

    # 将命令行中的字面量 \n 转为真正换行符（兼容 Windows PowerShell）
    title = args.title.replace('\\n', '\n')
    body  = args.body.replace('\\n', '\n')

    success = send_message(
        args.corpid, args.corpsecret, args.agentid,
        args.touser, title, body, args.msgtype, args.image
    )
    sys.exit(0 if success else 1)

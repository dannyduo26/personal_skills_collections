#!/usr/bin/env python3
# 企业微信信息查询脚本 / WeCom Corporate Information Query Script
import argparse
import urllib.request
import json
import sys
from utils import load_config, get_access_token

def get_department_list(dept_id=None):
    """获取部门列表 / Get department list"""
    token = get_access_token()
    if not token:
        return None
        
    url = f"https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token={token}"
    if dept_id:
        url += f"&id={dept_id}"
    
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get("errcode") == 0:
            return data.get("department", [])
        else:
            print(f"Error: 获取部门列表失败: {data.get('errmsg')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error: 请求部门列表异常: {e}", file=sys.stderr)
        return None

def get_userid_by_mobile(mobile):
    """根据手机号获取 UserId / Get UserId by mobile number"""
    token = get_access_token()
    if not token:
        return None

    url = f"https://qyapi.weixin.qq.com/cgi-bin/user/getuserid?access_token={token}"
    payload = {"mobile": mobile}
    encoded = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(url, data=encoded, method='POST',
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get("errcode") == 0:
            return data.get("userid")
        else:
            print(f"Error: 获取 UserId 失败: {data.get('errmsg')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error: 请求 UserId 异常: {e}", file=sys.stderr)
        return None


def get_userid_by_email(email):
    """根据邮箱获取 UserId / Get UserId by email"""
    token = get_access_token()
    if not token:
        return None

    # 企业微信 API：根据邮箱获取 userid
    # WeCom API: Get userid by email
    url = f"https://qyapi.weixin.qq.com/cgi-bin/user/get_userid_by_email?access_token={token}"
    payload = {"email": email, "email_type": 2}
    encoded = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(url, data=encoded, method='POST',
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get("errcode") == 0:
            return data.get("userid")
        else:
            print(f"Error: 获取 UserId 失败: {data.get('errmsg')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error: 请求 UserId 异常: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    # 强制设置输出编码为 UTF-8（Windows 环境下常见问题）
    # Force output encoding to UTF-8
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        sys.stdout.reconfigure(encoding='utf-8')

    config = load_config()
    
    parser = argparse.ArgumentParser(description="企业微信信息查询脚本")
    parser.add_argument("--corpid",     default=config.get("corpid"),     help="企业 ID")
    parser.add_argument("--corpsecret", default=config.get("corpsecret"), help="应用 Secret")
    parser.add_argument("--dept-id",    type=int,                         help="部门 ID（可选，不填则获取所有）")
    parser.add_argument("--mobile",     help="手机号（用于查询 UserId）")
    parser.add_argument("--email",      help="邮箱（用于查询 UserId）")
    
    args = parser.parse_args()

    if not args.corpid or not args.corpsecret:
        print("Error: 请在 config.json 或命令行中提供 corpid 和 corpsecret", file=sys.stderr)
        sys.exit(1)

    if args.mobile:
        # 获取 UserId
        print(f"正在查询手机号 {args.mobile} 对应的 UserId...")
        userid = get_userid_by_mobile(args.mobile)
        if userid:
            print(f"查询成功！UserId: {userid}")
        else:
            print("未能查询到对应的 UserId。")
    elif args.email:
        # 根据邮箱获取 UserId
        print(f"正在查询邮箱 {args.email} 对应的 UserId...")
        userid = get_userid_by_email(args.email)
        if userid:
            print(f"查询成功！UserId: {userid}")
        else:
            print("未能查询到对应的 UserId。")
    else:
        # 获取部门列表
        print("正在获取部门列表...")
        departments = get_department_list(args.dept_id)
        if departments is not None:
            print(f"{'ID':<10} {'名称 (Name)':<25} {'父部门ID (ParentID)'}")
            print("-" * 60)
            for dept in departments:
                name = dept.get('name', 'N/A')
                print(f"{dept.get('id'):<10} {name:<25} {dept.get('parentid')}")
        else:
            print("未能获取部门信息。")

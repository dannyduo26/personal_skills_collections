#!/usr/bin/env python3
# -*- coding: utf-8 import -*-
import json
import os
import sys
import argparse
import urllib.request
import urllib.parse
import time
from datetime import datetime

# Windows 终端编码处理
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')

def loadConfig():
    """加载配置文件 (小驼峰命名符合 Java 函数命名规则)"""
    configPath = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    if not os.path.exists(configPath):
        print(f"Error: 配置文件不存在: {configPath}")
        sys.exit(1)
    try:
        with open(configPath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: 读取配置文件失败: {e}")
        sys.exit(1)

def getGroupMsgHistory(apiUrl, accessToken, groupId, count=20, messageSeq=None):
    """获取群历史消息 (OneBot 11 get_group_msg_history API)"""
    url = f"{apiUrl}/get_group_msg_history"
    
    payload = {
        "group_id": int(groupId),
        "count": int(count),
        "reverseOrder": True
    }
    if messageSeq is not None:
        payload["message_seq"] = messageSeq
    
    headers = {
        "Content-Type": "application/json"
    }
    if accessToken:
        headers["Authorization"] = f"Bearer {accessToken}"
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: 请求 API 失败: {e}")
        return None

def formatTime(timestamp):
    """格式化时间戳"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def saveMessages(groupId, messages):
    """将消息保存到本地 logs 文件夹"""
    timeStr = datetime.now().strftime('%Y%m%d%H%M%S')
    fileName = f"group_{groupId}_{timeStr}.log"
    logsDir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    # 确保 logs 文件夹存在
    os.makedirs(logsDir, exist_ok=True)
    
    filePath = os.path.join(logsDir, fileName)
    try:
        with open(filePath, 'w', encoding='utf-8') as f:
            for msg in messages:
                json_line = json.dumps(msg, ensure_ascii=False)
                f.write(json_line + '\n')
        print(f"成功将消息保存到文件: {filePath}")
    except Exception as e:
        print(f"Error: 保存文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='获取 NapCat 群历史消息')
    parser.add_argument('-p', '--pages', type=int, default=10, help='获取的页数')
    parser.add_argument('-c', '--count', type=int, default=20, help='每页获取的消息数量 (建议不超过100)')
    parser.add_argument('-d', '--delay', type=float, default=1, help='分页请求之间的延迟秒数 (建议 0.5-2.0)')
    args = parser.parse_args()

    config = loadConfig()
    apiUrl = config.get('apiUrl', 'http://127.0.0.1:3000').rstrip('/')
    accessToken = config.get('accessToken', '')
    groupId = config.get('groupId')
    
    if not groupId or groupId == 123456789:
        print("Warning: 请在 config.json 中配置正确的 groupId")
        # 允许继续尝试，但提醒用户
    
    print(f"正在建立连接至: {apiUrl}")
    print(f"准备请求群组 {groupId} 的最近 {args.pages} 页消息...\n")
    
    allMessages = []
    currentSeq = None
    
    for i in range(args.pages):
        # 如果不是第一页且设置了延迟，则进行等待
        if i > 0 and args.delay > 0:
            print(f"等待 {args.delay} 秒以降低频率...")
            time.sleep(args.delay)

        print(f"\n-> [请求第 {i+1} 页] 请求参数: group_id={groupId}, count={args.count}, message_seq={currentSeq}, reverseOrder=True")
        result = getGroupMsgHistory(apiUrl, accessToken, groupId, count=args.count, messageSeq=currentSeq)
        
        if result and result.get('status') == 'ok':
            messages = result.get('data', {}).get('messages', [])
            if not messages:
                print(f"第 {i+1} 页未找到更多历史消息。")
                break
                
            allMessages.extend(messages)
            print(f"成功获取第 {i+1} 页, 共 {len(messages)} 条消息。")
            
            # 由于使用了 reverseOrder=True，最末尾（或最开头）的消息可能是最老的。
            # 这里稳妥起见，直接在拿到的消息中找出时间最早的，取其 message_seq
            try:
                oldestMsg = min(messages, key=lambda x: x.get('time', 0))
                currentSeq = oldestMsg['message_seq']
            except (KeyError, IndexError, ValueError):
                print("Warning: 无法从消息体中提取 message_seq，无法继续向后分页。")
                break
        else:
            status = result.get('status') if result else "Unknown"
            msg = result.get('msg') if result else "No response"
            print(f"获取第 {i+1} 页失败 (Status: {status}, Msg: {msg})")
            if i == 0:
                print("请检查 NapCat 是否已启动并开启了 HTTP 服务。")
            break
            
    if allMessages:
        # 去重并按时间排序 (以防发生重叠)
        uniqueMessages = {msg.get('message_id', id(msg)): msg for msg in allMessages}
        finalMessages = sorted(uniqueMessages.values(), key=lambda x: x.get('time', 0))
        
        print(f"\n整体获取并最终整理了 {len(finalMessages)} 条不重复的历史消息。")
        saveMessages(groupId, finalMessages)
    else:
        print("未能获取到任何历史消息。")

if __name__ == "__main__":
    main()

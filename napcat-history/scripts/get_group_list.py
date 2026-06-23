#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import urllib.request
from datetime import datetime

# 处理 Windows 终端输出 UTF-8 中文
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')

def loadConfig():
    """读取配置文件"""
    configPath = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    if not os.path.exists(configPath):
        print(f"Error: 找不到配置文件 {configPath}")
        sys.exit(1)
    try:
        with open(configPath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: 解析配置失败: {e}")
        sys.exit(1)

def getGroupList(apiUrl, accessToken):
    """请求 NapCat 获取所有群组的列表"""
    url = f"{apiUrl}/get_group_list"
    headers = {"Content-Type": "application/json"}
    if accessToken:
        headers["Authorization"] = f"Bearer {accessToken}"

    # get_group_list 支持 POST 请求不需要参数
    req = urllib.request.Request(url, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: HTTP 请求失败 - {e}")
        return None

def saveGroupList(groups):
    """保存获取到的群列表数据到日志文件"""
    # 获取当前时间
    timeStr = datetime.now().strftime('%Y%m%d%H%M%S')
    fileName = f"group_list_{timeStr}.log"
    logsDir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    os.makedirs(logsDir, exist_ok=True)
    filePath = os.path.join(logsDir, fileName)
    
    try:
        with open(filePath, 'w', encoding='utf-8') as f:
            json.dump(groups, f, indent=4, ensure_ascii=False)
        print(f"\n已将完整的群组列表保存到: {filePath}")
    except Exception as e:
        print(f"Error: 保存文件失败 - {e}")

def main():
    config = loadConfig()
    apiUrl = config.get('apiUrl', 'http://127.0.0.1:3000').rstrip('/')
    accessToken = config.get('accessToken', '')
    
    print(f"正在连接到: {apiUrl} ...\n")
    
    result = getGroupList(apiUrl, accessToken)
    if result and result.get('status') == 'ok':
        groups = result.get('data', [])
        print(f"成功获取到了 {len(groups)} 个 QQ 群：\n")
        
        # 打印部分群组核心信息
        for index, group in enumerate(groups, start=1):
            groupName = group.get('group_name', '未知群名')
            groupId = group.get('group_id', '未知群号')
            memberCount = group.get('member_count', 0)
            maxMemberCount = group.get('max_member_count', 0)
            print(f"[{index}] {groupName} (群号: {groupId}) | 人数: {memberCount}/{maxMemberCount}")
            
        saveGroupList(groups)
    else:
        status = result.get('status') if result else "Unknown"
        msg = result.get('msg') if result else "No Response"
        print(f"获取群列表失败: Status={status}, Message={msg}")
        print("请检查 NapCat/OneBot 进程是否启动并允许了 HTTP API 调用。")

if __name__ == "__main__":
    main()

import asyncio
import sys
import os
import json

# Add the scripts directory to sys.path
# 将 scripts 目录添加到 sys.path 以便导入 request 模块
scripts_path = os.path.dirname(os.path.dirname(__file__))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from request.web.xhs_session import create_xhs_session

async def main():
    # extraction of note_id and xsec_token from user URL
    # 从用户提供的 URL 中提取的 note_id 和 xsec_token
    note_id = "69aa3526000000000e03dba5"
    xsec_token = "ABZlhnqE5svF4ns_MrUQdrzfgdeL94ZMgQMRUNdL7w4js"
    
    # User provided cookies string
    # 用户提供的完整 Cookie 字符串
    cookie_str = (
        "gid=yj4q0WYD2YUKyj4q0WY0qvuMY09hf7djT4VvTxDAi99Y6328JKUdC3888J2J4YJ88f2yfDd8; "
        "customerClientId=778030908143996; x-user-id-miniapp.xiaohongshu.com=5e055cc7000000000100017c; "
        "x-user-id-creator.xiaohongshu.com=5cd677dd0000000017006202; x-user-id-idea.xiaohongshu.com=5c6293ca00000000100043f3; "
        "abRequestId=a4df5aa4-57c2-54c0-9db9-790deda2b378; a1=19b9c58e9a72tznbrnd68nfy5izhcrmwh6yn0hs9950000427284; "
        "webId=51ac5d086f077b3580247f483fec5f07; web_session=0400698f711f8f56512aa7749b3b4b9e3196fc; "
        "id_token=VjEAANmEt4eRahGfZBQ/e6gJgiOB2N7EDp6lKbKjz2xpIk873rQVYCtHs1Ol4RVcGXLTcwgEX6nBBm/XqGkvC8/CuA1dA7iBy+OVYXN/3LaiyWCcKp7oNA5Pry9VRvK1glVJ6WSf; "
        "webBuild=6.1.0; xsecappid=xhs-pc-web; acw_tc=0a0bb1f417738254256075291e2d7cef740dde1a0fe02c0bba3317ad83d012; "
        "websectiga=f3d8eaee8a8c63016320d94a1bd00562d516a5417bc43a032a80cbf70f07d5c0; "
        "sec_poison_id=c4c839b2-a522-4a9f-8187-e5231d3a23b5; loadts=1773825781980"
    )
    
    # Parse cookies
    cookies = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            k, v = item.strip().split('=', 1)
            cookies[k] = v
            
    web_session = cookies.get('web_session')
    
    # Create session
    xhs = await create_xhs_session(proxy=None, web_session=web_session)
    
    # Manually inject all user cookies
    for k, v in cookies.items():
        xhs._session.cookie_jar.update_cookies({k: v})
    
    try:
        # Fetch note detail
        # 获取笔记详情
        print(f"Fetching details for note_id: {note_id}...")
        
        # Use the requested API
        res = await xhs.apis.note.note_detail(note_id, xsec_token)
        data = await res.json()
        
        # Output results
        # 输出提取的结果
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            if items:
                note_card = items[0].get("note_card", {})
                print("\n--- Note Content ---")
                print(f"Title: {note_card.get('title')}")
                print(f"Author: {note_card.get('user', {}).get('nickname')}")
                print(f"Desc: {note_card.get('desc')}")
                print(f"Likes: {note_card.get('interact_info', {}).get('liked_count')}")
                print(f"Collects: {note_card.get('interact_info', {}).get('collected_count')}")
                print(f"Comments: {note_card.get('interact_info', {}).get('comment_count')}")
            else:
                print("No note items found in response.")
        else:
            print(f"Error fetching note: {data}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close session
        # 关闭会话
        await xhs.close_session()

if __name__ == "__main__":
    asyncio.run(main())

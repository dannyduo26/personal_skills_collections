import asyncio
import sys
import os
import json

# Add the scripts directory to sys.path
scripts_path = os.path.dirname(os.path.dirname(__file__))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from request.web.xhs_session import create_xhs_session

async def test_user_notes():
    # User info from provided URL
    # 用户信息
    user_id = "5c6293ca00000000100043f3"
    xsec_token = "ABcK8YTACaRsDM0BRomKvwyNSVIUQ8lEfVwZidI6m0r_w="
    xsec_source = "pc_search"
    
    # User provided cookies string
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
        # Fetch user notes
        # 获取用户笔记列表
        print(f"Fetching notes for user_id: {user_id}...")
        res = await xhs.apis.note.search_user_notes(user_id, xsec_token=xsec_token, xsec_source=xsec_source)
        data = await res.json()
        
        if data.get("code") == 0:
            notes = data.get("data", {}).get("notes", [])
            print(f"\n--- User Notes ({len(notes)}) ---")
            for note in notes:
                title = note.get('display_title') or note.get('title')
                note_id = note.get('note_id')
                likes = note.get('interact_info', {}).get('liked_count')
                print(f"[{note_id}]: {title} (Likes: {likes})")
        else:
            print(f"Error fetching user notes: {data}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await xhs.close_session()

if __name__ == "__main__":
    asyncio.run(test_user_notes())

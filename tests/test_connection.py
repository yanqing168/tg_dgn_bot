#!/usr/bin/env python3
"""
测试Telegram连接
"""

import asyncio
import httpx
from src.config import settings

async def test_telegram_connection():
    """测试连接到Telegram API"""
    print(f"测试Bot Token: {settings.bot_token[:10]}...")
    
    # 测试基本网络连接
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 先测试能否访问Telegram API
            response = await client.get("https://api.telegram.org")
            print(f"✅ 可以访问 Telegram API (状态码: {response.status_code})")
    except Exception as e:
        print(f"❌ 无法访问 Telegram API: {e}")
        return False
    
    # 测试Bot Token
    url = f"https://api.telegram.org/bot{settings.bot_token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    print(f"✅ Bot Token 有效")
                    print(f"   Bot用户名: @{bot_info.get('username')}")
                    print(f"   Bot名称: {bot_info.get('first_name')}")
                    return True
                else:
                    print(f"❌ Bot Token 无效: {data.get('description')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"❌ 连接错误: {e}")
    
    return False

if __name__ == "__main__":
    result = asyncio.run(test_telegram_connection())
    if not result:
        print("\n可能的解决方案：")
        print("1. 检查网络连接和防火墙设置")
        print("2. 确认Bot Token是否正确")
        print("3. 使用代理或VPN")
        print("4. 增加超时时间")

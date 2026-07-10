"""完整聊天流程测试"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_full_flow():
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. 注册/登录
        print("=" * 50)
        print("1. 注册新用户")
        print("=" * 50)
        reg = await client.post(f"{BASE_URL}/api/v1/auth/register", json={
            "phone": "13900001111",
            "password": "test123456",
            "nickname": "流程测试",
            "birth_date": "1995-06-15"
        })
        print(f"   状态: {reg.status_code}")
        if reg.status_code == 200:
            token = reg.json()["access_token"]
        else:
            print(f"   注册失败，尝试登录...")
            login = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
                "phone": "13900001111",
                "password": "test123456"
            })
            token = login.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 获取用户信息
        me = await client.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
        user_id = me.json()["id"]
        print(f"   用户ID: {user_id}")
        
        # 2. 获取角色列表
        print("\n" + "=" * 50)
        print("2. 获取角色列表")
        print("=" * 50)
        chars = await client.get(f"{BASE_URL}/api/v1/characters", headers=headers)
        characters = chars.json()
        for c in characters:
            print(f"   - {c['id']}: {c['name']} ({c['personality']})")
        
        # 3. 选择角色
        character_id = characters[0]["id"]
        print(f"\n" + "=" * 50)
        print(f"3. 选择角色: {character_id}")
        print("=" * 50)
        sel = await client.post(
            f"{BASE_URL}/api/v1/characters/select",
            json={"character_id": character_id},
            headers=headers
        )
        print(f"   选择状态: {sel.status_code}")
        
        # 4. 发送聊天消息 (SSE 流式)
        print(f"\n" + "=" * 50)
        print(f"4. 发送聊天消息 (SSE 流式)")
        print("=" * 50)
        
        test_messages = [
            "你好呀，今天心情怎么样？",
            "最近工作压力好大，总是加班",
            "你有什么好的放松方式吗？",
        ]
        
        for msg in test_messages:
            print(f"\n   用户: {msg}")
            print(f"   AI: ", end="", flush=True)
            
            full_reply = ""
            async with client.stream(
                "POST",
                f"{BASE_URL}/api/v1/chat/{character_id}/message",
                json={"content": msg},
                headers=headers,
                timeout=60.0
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    print(f"\n   错误 ({resp.status_code}): {body.decode()}")
                    continue
                
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        if data.startswith("{") and "message_id" in data:
                            continue
                        full_reply += data
                        print(data, end="", flush=True)
            
            print()
        
        # 5. 查看聊天记录
        print(f"\n" + "=" * 50)
        print("5. 查看聊天记录")
        print("=" * 50)
        history = await client.get(
            f"{BASE_URL}/api/v1/chat/{character_id}/history",
            params={"limit": 20, "offset": 0},
            headers=headers
        )
        messages = history.json()["messages"]
        print(f"   共 {len(messages)} 条消息")
        for m in messages[-6:]:
            role = "用户" if m["role"] == "user" else "AI"
            content = m["content"][:50] + "..." if len(m["content"]) > 50 else m["content"]
            print(f"   [{role}] {content}")
        
        # 6. 查看记忆
        print(f"\n" + "=" * 50)
        print("6. 查看记忆")
        print("=" * 50)
        memories = await client.get(
            f"{BASE_URL}/api/v1/memory/{character_id}",
            headers=headers
        )
        mem_data = memories.json()
        mem_list = mem_data.get("memories", [])
        print(f"   共 {mem_data.get('total', 0)} 条记忆")
        for m in mem_list[:5]:
            print(f"   - [{m['category']}] {m['content'][:50]}... (重要度: {m['importance']})")
        
        # 7. 查看关系
        print(f"\n" + "=" * 50)
        print("7. 查看关系")
        print("=" * 50)
        rel = await client.get(
            f"{BASE_URL}/api/v1/characters/{character_id}/relation",
            headers=headers
        )
        if rel.status_code == 200:
            r = rel.json()
            print(f"   关系等级: {r.get('level', 'unknown')}")
            print(f"   亲密度: {r.get('intimacy', 0)}")
            print(f"   连续互动: {r.get('consecutive_days', 0)} 天")
        
        # 8. 查看情绪日记
        print(f"\n" + "=" * 50)
        print("8. 查看情绪日记")
        print("=" * 50)
        emotion = await client.get(
            f"{BASE_URL}/api/v1/emotion/diary",
            params={"limit": 5, "offset": 0},
            headers=headers
        )
        emo_data = emotion.json()
        emo_list = emo_data.get("entries", [])
        print(f"   共 {len(emo_list)} 条记录")
        for e in emo_list[:3]:
            print(f"   - {e.get('date')}: {e.get('dominant_emotion')} (强度: {e.get('intensity')})")
        
        print(f"\n" + "=" * 50)
        print("完整流程测试完成!")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_full_flow())

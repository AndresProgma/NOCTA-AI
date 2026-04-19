import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from TikTokApi import TikTokApi
from services.scraping import get_user_videos, get_comments_for_video
from services.analytics import analyze_competitor

ms_token = os.environ.get("ms_token", None)


async def run_pipeline(username: str, video_count: int = 5, comments_per_video: int = 20) -> dict:
    print(f"\n🚀 Iniciando pipeline de competidor: '@{username}'")
    print("=" * 50)

    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )

        # Etapa 1: perfil del competidor
        print(f"\n👤 Etapa 1: Obteniendo perfil de @{username}...")
        user = api.user(username)
        user_data = await user.info()
        stats = user_data.get("userInfo", {}).get("stats", {})
        bio = user_data.get("userInfo", {}).get("user", {}).get("signature", "")
        print(f"   → Seguidores: {stats.get('followerCount', 'N/A')}")
        print(f"   → Bio: {bio}")

        # Etapa 2: últimos N videos
        print(f"\n📹 Etapa 2: Obteniendo últimos {video_count} videos...")
        videos = await get_user_videos(api, username, count=video_count)
        print(f"   → {len(videos)} videos encontrados")

        # Etapa 3: comentarios de cada video
        print(f"\n💬 Etapa 3: Extrayendo comentarios ({comments_per_video} por video)...")
        all_texts = []
        for video in videos:
            if video["descripcion"]:
                all_texts.append(video["descripcion"])
            comments = await get_comments_for_video(api, video["id"], count=comments_per_video)
            all_texts.extend(comments)
            print(f"   → Video {video['id']}: {len(comments)} comentarios")

        print(f"   → Total textos recolectados: {len(all_texts)}")

    # Etapa 4: análisis de competidor con IA
    print(f"\n🧠 Etapa 4: Analizando qué está funcionando para @{username}...")
    insights = analyze_competitor(username, all_texts)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(insights, indent=2, ensure_ascii=False))

    return insights


if __name__ == "__main__":
    asyncio.run(run_pipeline("therock", video_count=3, comments_per_video=10))

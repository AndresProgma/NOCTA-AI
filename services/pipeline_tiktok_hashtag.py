import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from TikTokApi import TikTokApi
from services.scraping import search_videos, get_comments_for_video
from services.analytics import analyze_signals

ms_token = os.environ.get("ms_token", None)


async def run_pipeline(keyword: str, video_count: int = 5, comments_per_video: int = 20) -> dict:
    print(f"\n🚀 Iniciando pipeline para: '{keyword}'")
    print("=" * 50)

    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )

        # Etapa 1: buscar videos por keyword
        print(f"\n📹 Etapa 1: Buscando {video_count} videos sobre '{keyword}'...")
        videos = await search_videos(api, keyword, count=video_count)
        print(f"   → {len(videos)} videos encontrados")

        # Etapa 2: recolectar descripciones + comentarios de cada video
        print(f"\n💬 Etapa 2: Extrayendo comentarios ({comments_per_video} por video)...")
        all_texts = []
        for video in videos:
            if video["descripcion"]:
                all_texts.append(video["descripcion"])
            comments = await get_comments_for_video(api, video["id"], count=comments_per_video)
            all_texts.extend(comments)
            print(f"   → Video {video['id']}: {len(comments)} comentarios")

        print(f"   → Total textos recolectados: {len(all_texts)}")
        print(f"   [DEBUG textos]: {all_texts[:3]}")  # muestra los primeros 3

    # Etapa 3: análisis semántico con Groq
    print(f"\n🧠 Etapa 3: Analizando señales con IA...")
    insights = analyze_signals(keyword, all_texts)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(insights, indent=2, ensure_ascii=False))

    return insights


if __name__ == "__main__":
    asyncio.run(run_pipeline("#nopuedobajardepeso", video_count=3, comments_per_video=10))

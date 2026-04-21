import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import get_trending_videos
from services.analytics import analyze_signals, build_transcription_context
from services.session_config import create_sessions_with_retry, select_region, ask_transcription
from services.human_pace import fetch_comments_safe, delay_between_videos

load_dotenv()
ms_token = os.environ.get("ms_token", None)

PIPELINE_NAME = "tiktok_trending"

"""Este pipeline accede al feed de contenido viral de TikTok sin filtro de nicho ni categoría. Analiza cada video
  individualmente: sus propios comentarios y transcripción, generando insights específicos por video.

  Para qué sirve a Nocta: Detectar tendencias emergentes antes de que se saturen, con contexto completo
  de lo que dice el creador y cómo responde su audiencia, video por video."""


async def run_pipeline(video_count: int = 2, comments_per_video: int = 10, api=None, country: str | None = None, transcribe: bool = False) -> dict:
    # Analiza cada video trending individualmente con sus propios comentarios y transcripción.
    print(f"\n🚀 Iniciando pipeline de tendencias globales TikTok")
    print("=" * 50)

    async def _run(api):
        print(f"\n🔥 Etapa 1: Obteniendo {video_count} videos trending...")
        videos = await get_trending_videos(api, count=video_count)
        print(f"   → {len(videos)} videos obtenidos")

        resultados = {}
        for i, video in enumerate(videos, 1):
            video_id = video.get("id")
            desc = (video.get("descripcion") or f"video_{video_id}")[:60]
            video_url = video.get("url", f"https://www.tiktok.com/@{video.get('autor', '')}/video/{video_id}")
            print(f"\n{'='*50}")
            print(f"🎥 VIDEO {i}/{len(videos)}: {desc}")
            print(f"🔗 {video_url}")
            print("=" * 50)

            texts = [video["descripcion"]] if video.get("descripcion") else []

            print(f"   💬 Obteniendo comentarios...")
            comments = await fetch_comments_safe(api, video_id, comments_per_video)
            texts.extend(comments)
            print(f"   → {len(comments)} comentarios obtenidos")

            video_context = ""
            if transcribe:
                print(f"   🎙️  Transcribiendo video...")
                video_context = await build_transcription_context(api, [video])
                if video_context:
                    print(f"\n   📄 Transcripción:")
                    print("   " + "-" * 48)
                    print(video_context)
                    print("   " + "-" * 48)

            print(f"   🧠 Analizando señales del video...")
            insights = analyze_signals(desc, texts, video_context=video_context)
            print(json.dumps(insights, indent=2, ensure_ascii=False))
            resultados[video_id] = {"video": desc, "insights": insights}

            if i < len(videos):
                await delay_between_videos()

        return resultados

    if api is not None:
        resultados = await _run(api)
    else:
        async with TikTokApi() as api:
            await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
            resultados = await _run(api)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    return resultados


if __name__ == "__main__":
    country = select_region()
    transcribe = ask_transcription()
    asyncio.run(run_pipeline(video_count=1, comments_per_video=20, country=country, transcribe=transcribe))

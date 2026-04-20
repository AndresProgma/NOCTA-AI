import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import get_trending_videos
from services.analytics import analyze_signals
from services.session_config import create_sessions_with_retry, select_region
from services.human_pace import collect_texts_from_videos

load_dotenv()
ms_token = os.environ.get("ms_token", None)

PIPELINE_NAME = "tiktok_trending"

"""Este pipeline accede al feed de contenido viral de TikTok sin filtro de nicho ni categoría. Captura los videos con mayor tracción del
  momento, analiza sus comentarios y detecta patrones emergentes: temas que están ganando atención, lenguaje nuevo que está adoptando la
  audiencia, formatos de contenido que están generando engagement.

  Para qué sirve a Nocta: El tiempo lo es todo en marketing de contenido. Este pipeline le da a Nocta la capacidad de identificar
  oportunidades de nicho antes de que se vuelvan obvias para todos. Un cliente que entra a una tendencia en su fase temprana tiene una
  ventaja competitiva real. También sirve para detectar cambios culturales y de lenguaje que afectan cómo se comunican los mercados."""


async def run_pipeline(video_count: int = 2, comments_per_video: int = 10, api=None, country: str | None = None) -> dict:
    # Captura los videos más virales del momento en TikTok sin filtro de nicho.
    # Nocta lo usa para detectar tendencias emergentes y oportunidades de nicho antes de que se saturen.
    print(f"\n🚀 Iniciando pipeline de tendencias globales TikTok")
    print("=" * 50)

    async def _run(api):
        print(f"\n🔥 Etapa 1: Obteniendo {video_count} videos trending...")
        videos = await get_trending_videos(api, count=video_count)
        print(f"   → {len(videos)} videos obtenidos")

        print(f"\n💬 Etapa 2: Extrayendo comentarios (modo humano)...")
        all_texts = await collect_texts_from_videos(api, videos, comments_per_video)
        print(f"   → Total textos recolectados: {len(all_texts)}")
        return all_texts

    if api is not None:
        all_texts = await _run(api)
    else:
        async with TikTokApi() as api:
            await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
            all_texts = await _run(api)

    print(f"\n🧠 Etapa 3: Detectando nichos y oportunidades emergentes...")
    insights = analyze_signals("tendencias globales TikTok", all_texts)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(insights, indent=2, ensure_ascii=False))

    return insights


if __name__ == "__main__":
    asyncio.run(run_pipeline(video_count=2, comments_per_video=10, country=select_region()))

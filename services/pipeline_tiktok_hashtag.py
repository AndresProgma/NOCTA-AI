import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import get_videos_by_hashtag
from services.analytics import analyze_signals, build_transcription_context
from services.session_config import create_sessions_with_retry, select_region, ask_transcription
from services.human_pace import collect_texts_from_videos

load_dotenv()
ms_token = os.environ.get("ms_token", None)
print(f"[DEBUG] ms_token cargado: {ms_token[:30] if ms_token else 'NONE ❌'}")

PIPELINE_NAME = "tiktok_hashtag"

""" Este pipeline toma un hashtag como punto de entrada y extrae las conversaciones reales que ocurren alrededor de ese tema en TikTok. Accede
  a los videos más relevantes del hashtag, recolecta los comentarios de la audiencia y los procesa con el motor de análisis semántico de
  Nocta para identificar fricciones, intenciones de compra y patrones de lenguaje recurrentes.

  Para qué sirve a Nocta: Cuando un cliente quiere entrar a un nicho o lanzar un producto, este pipeline responde la pregunta más importante
  antes de invertir: ¿qué está diciendo realmente la audiencia sobre este tema? No métricas de vanidad, sino el texto crudo de personas
  reales expresando sus problemas, frustraciones y deseos. Es la base para construir mensajes de venta que conectan."""

async def run_pipeline(keyword: str, video_count: int = 2, comments_per_video: int = 10, api=None, country: str | None = None, transcribe: bool = False) -> dict:
    # Analiza un hashtag específico para descubrir qué dice la audiencia en TikTok.
    # Nocta lo usa para entender los dolores, deseos e intenciones de compra reales de un nicho.
    print(f"\n🚀 Iniciando pipeline para: '{keyword}'")
    print("=" * 50)

    async def _run(api):
        hashtag = keyword.lstrip("#")
        print(f"\n📹 Etapa 1: Buscando {video_count} videos para #{hashtag}...")
        videos = await get_videos_by_hashtag(api, hashtag, count=video_count)
        print(f"   → {len(videos)} videos encontrados")

        print(f"\n💬 Etapa 2: Extrayendo comentarios (modo humano)...")
        all_texts = await collect_texts_from_videos(api, videos, comments_per_video)
        print(f"   → Total textos recolectados: {len(all_texts)}")

        video_context = ""
        if transcribe:
            print(f"\n🎙️  Etapa 2.5: Transcribiendo videos...")
            video_context = await build_transcription_context(api, videos)

        return all_texts, video_context

    if api is not None:
        all_texts, video_context = await _run(api)
    else:
        async with TikTokApi() as api:
            await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
            all_texts, video_context = await _run(api)

    if video_context:
        print(f"\n📄 Contexto de transcripciones:")
        print("-" * 50)
        print(video_context)
        print("-" * 50)

    print(f"\n🧠 Etapa 3: Analizando señales con IA...")
    insights = analyze_signals(keyword, all_texts, video_context=video_context)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(insights, indent=2, ensure_ascii=False))

    return insights


if __name__ == "__main__":
    country = select_region()
    transcribe = ask_transcription()
    asyncio.run(run_pipeline("#exparejas", video_count=2, comments_per_video=10, country=country, transcribe=transcribe))

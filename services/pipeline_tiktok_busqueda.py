import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import search_videos
from services.analytics import analyze_signals, build_transcription_context
from services.session_config import create_sessions_with_retry, select_region, ask_transcription
from services.human_pace import collect_texts_from_videos

load_dotenv()
ms_token = os.environ.get("ms_token", None)
print(f"[DEBUG] ms_token cargado: {ms_token[:30] if ms_token else 'NONE ❌'}")

PIPELINE_NAME = "tiktok_busqueda"

"""Este pipeline recibe cualquier término de búsqueda libre y encuentra los videos más relevantes que TikTok devuelve para ese tema,
  igual que cuando un usuario escribe algo en el buscador de TikTok. No depende de hashtags — el algoritmo agrupa por contexto semántico.

  Para qué sirve a Nocta: Permite explorar cualquier tema, producto, dolor o nicho y ver qué contenido está funcionando realmente.
  Útil para descubrir ángulos de contenido, analizar cómo habla la audiencia sobre un tema, o estudiar qué formatos generan más
  engagement antes de producir contenido propio."""

async def run_pipeline(query: str, video_count: int = 5, comments_per_video: int = 10, api=None, country: str | None = None, transcribe: bool = False) -> dict:
    print(f"\n🚀 Iniciando búsqueda para: '{query}'")
    print("=" * 50)

    async def _run(api):
        print(f"\n📹 Etapa 1: Buscando {video_count} videos para '{query}'...")
        videos = await search_videos(api, query, count=video_count)
        print(f"   → {len(videos)} videos encontrados")

        if not videos:
            print("   ⚠️  Sin resultados para esa búsqueda.")
            return [], ""

        print(f"\n🔗 Videos encontrados:")
        for i, v in enumerate(videos, 1):
            print(f"   {i}. {v.get('url')} — {v.get('descripcion', '')[:80]}")

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

    if not all_texts:
        return {}

    if video_context:
        print(f"\n📄 Contexto de transcripciones:")
        print("-" * 50)
        print(video_context)
        print("-" * 50)

    print(f"\n🧠 Etapa 3: Analizando señales con IA...")
    insights = analyze_signals(query, all_texts, video_context=video_context)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(insights, indent=2, ensure_ascii=False))

    return insights


if __name__ == "__main__":
    query = input("🔍 ¿Qué querés buscar en TikTok? → ").strip()
    country = select_region()
    transcribe = ask_transcription()
    asyncio.run(run_pipeline(query, video_count=5, comments_per_video=10, country=country, transcribe=transcribe))

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

PIPELINE_NAME = "tiktok_validacion"
"""Este pipeline recibe una lista de keywords — distintas formas de nombrar el mismo problema o deseo — y las analiza en paralelo en TikTok.
  Mide cuál de ellas genera más fricción, más intención de compra y más volumen de conversación real. Al final entrega un ranking comparativo   con el ganador en cada dimensión.

  Para qué sirve a Nocta: Antes de escribir un anuncio, un email o una página de ventas, la pregunta crítica es: ¿cómo llama mi audiencia a
  su propio problema? "Bajar de peso", "quemar grasa" y "perder barriga" significan lo mismo pero generan reacciones distintas en audiencias
  distintas. Este pipeline elimina la adivinanza y determina con datos cuál es el ángulo de mensaje que más conecta antes de invertir en
  producción o pauta. Es una validación de mercado rápida, económica y basada en comportamiento real, no en suposiciones o tendencias superficiales."""

async def run_pipeline(keywords: list[str], video_count: int = 2, comments_per_video: int = 10, api=None, country: str | None = None, transcribe: bool = False) -> dict:
    # Compara varias keywords en paralelo midiendo fricción e intención de compra en cada una.
    # Nocta lo usa para validar qué ángulo de mensaje conecta más con la audiencia antes de invertir en contenido o ads.
    print(f"\n🚀 Iniciando pipeline de validación de keywords")
    print(f"   Keywords a comparar: {keywords}")
    print("=" * 50)

    async def _run(api):
        resultados = {}
        for keyword in keywords:
            print(f"\n🔍 Procesando keyword: '{keyword}'")

            print(f"   📹 Buscando {video_count} videos...")
            videos = await search_videos(api, keyword, count=video_count)
            print(f"   → {len(videos)} videos encontrados")

            print(f"   💬 Extrayendo comentarios (modo humano)...")
            all_texts = await collect_texts_from_videos(api, videos, comments_per_video)
            print(f"   → Total textos: {len(all_texts)}")

            video_context = ""
            if transcribe:
                print(f"   🎙️  Transcribiendo videos de '{keyword}'...")
                video_context = await build_transcription_context(api, videos)
                if video_context:
                    print(f"\n   📄 Contexto '{keyword}':")
                    print("   " + "-" * 48)
                    print(video_context)
                    print("   " + "-" * 48)

            print(f"   🧠 Analizando señales...")
            resultados[keyword] = analyze_signals(keyword, all_texts, video_context=video_context)
        return resultados

    if api is not None:
        resultados = await _run(api)
    else:
        async with TikTokApi() as api:
            await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
            resultados = await _run(api)

    comparacion = {
        "keywords_analizadas": keywords,
        "resultados_por_keyword": resultados,
        "ganador_friccion": max(resultados, key=lambda k: len(resultados[k].get("fricciones", []))),
        "ganador_intencion": max(resultados, key=lambda k: len(resultados[k].get("intenciones", []))),
    }

    print("\n✅ Pipeline de validación completado")
    print("=" * 50)
    print(json.dumps(comparacion, indent=2, ensure_ascii=False))

    return comparacion


if __name__ == "__main__":
    country = select_region()
    transcribe = ask_transcription()
    asyncio.run(run_pipeline(
        keywords=["bajar de peso", "quemar grasa", "perder barriga"],
        video_count=2,
        comments_per_video=10,
        country=country,
        transcribe=transcribe,
    ))

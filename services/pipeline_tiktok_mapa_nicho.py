import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import get_videos_by_hashtag
from services.analytics import analyze_signals
from services.session_config import create_sessions_with_retry, select_region
from services.human_pace import collect_texts_from_videos

load_dotenv()
ms_token = os.environ.get("ms_token", None)

PIPELINE_NAME = "tiktok_mapa_nicho"

"""Este pipeline recibe un nicho completo definido por múltiples hashtags relacionados y los analiza en una sola ejecución unificada. En lugar   
  de ver un hashtag de forma aislada, consolida todas las conversaciones del ecosistema de un mercado para construir una visión panorámica:
  qué lenguaje usa la audiencia, qué problemas se repiten, qué soluciones buscan, qué emociones dominan.

  Para qué sirve a Nocta: Es la herramienta de investigación de mercado más completa del sistema. Antes de crear contenido, definir una
  oferta o posicionar un producto, este pipeline entrega el mapa completo de un nicho basado en comportamiento real. Permite a los clientes
  de Nocta tomar decisiones estratégicas con evidencia, no suposiciones."""


async def run_pipeline(nicho: str, hashtags: list[str], videos_por_hashtag: int = 2, comments_per_video: int = 5, api=None, country: str | None = None) -> dict:
    # Analiza múltiples hashtags de un mismo nicho en una sola pasada para construir una visión completa del mercado.
    # Nocta lo usa para mapear las conversaciones clave de un nicho antes de crear contenido o lanzar una oferta.
    print(f"\n🚀 Iniciando pipeline de mapa de nicho: '{nicho}'")
    print(f"   Hashtags: {hashtags}")
    print("=" * 50)

    async def _run(api):
        all_texts = []
        for hashtag in hashtags:
            print(f"\n🏷️  Buscando videos para #{hashtag}...")
            videos = await get_videos_by_hashtag(api, hashtag, count=videos_por_hashtag)
            print(f"   → {len(videos)} videos encontrados")

            print(f"   💬 Extrayendo comentarios (modo humano)...")
            texts = await collect_texts_from_videos(api, videos, comments_per_video)
            all_texts.extend(texts)

        print(f"\n   → Total textos agregados del nicho: {len(all_texts)}")
        return all_texts

    if api is not None:
        all_texts = await _run(api)
    else:
        async with TikTokApi() as api:
            await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
            all_texts = await _run(api)

    print(f"\n🧠 Etapa final: Construyendo mapa completo del nicho '{nicho}'...")
    insights = analyze_signals(nicho, all_texts)

    resultado = {
        "nicho": nicho,
        "hashtags_analizados": hashtags,
        "total_textos": len(all_texts),
        "mapa": insights,
    }

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    return resultado


if __name__ == "__main__":
    asyncio.run(run_pipeline(
        nicho="suplementos deportivos",
        hashtags=["proteina", "creatina", "preworkout", "suplementosdeportivos"],
        videos_por_hashtag=2,
        comments_per_video=10,
        country=select_region(),
    ))

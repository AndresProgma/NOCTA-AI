import asyncio
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import get_user_videos
from services.analytics import analyze_competitor
from services.session_config import create_sessions_with_retry, select_region
from services.human_pace import collect_texts_from_videos

load_dotenv()
ms_token = os.environ.get("ms_token", None)

PIPELINE_NAME = "tiktok_cuenta"

"""Este pipeline apunta directamente a una cuenta específica de TikTok — un competidor o referente del nicho — y extrae sus videos más
  recientes junto con los comentarios que generaron. Analiza qué tipo de contenido produce esa cuenta, cómo responde su audiencia y qué
  señales de compra o rechazo aparecen en esas conversaciones.

  Para qué sirve a Nocta: La inteligencia competitiva es uno de los activos más valiosos en marketing digital. Este pipeline convierte el
  éxito ajeno en información accionable: qué ángulos de contenido están funcionando en el mercado, qué promesas resuenan con la audiencia,
  qué objeciones aparecen en los comentarios. Los clientes de Nocta pueden aprender de quien ya está ganando sin tener que experimentar desde   cero."""



async def run_pipeline(username: str, video_count: int = 2, comments_per_video: int = 10, api=None, country: str | None = None) -> dict:
    # Espía una cuenta competidora: extrae sus videos y los comentarios que generan para entender qué resuena con su audiencia.
    # Nocta lo usa para identificar ángulos de contenido ganadores y qué tipo de oferta está funcionando en el nicho.
    print(f"\n🚀 Iniciando pipeline de competidor: '@{username}'")
    print("=" * 50)

    async def _run(api):
        print(f"\n👤 Etapa 1: Obteniendo perfil de @{username}...")
        user = api.user(username)
        user_data = await user.info()
        stats = user_data.get("userInfo", {}).get("stats", {})
        bio = user_data.get("userInfo", {}).get("user", {}).get("signature", "")
        print(f"   → Seguidores: {stats.get('followerCount', 'N/A')}")
        print(f"   → Bio: {bio}")

        print(f"\n📹 Etapa 2: Obteniendo últimos {video_count} videos...")
        videos = await get_user_videos(api, username, count=video_count)
        print(f"   → {len(videos)} videos encontrados")

        print(f"\n💬 Etapa 3: Extrayendo comentarios (modo humano)...")
        all_texts = await collect_texts_from_videos(api, videos, comments_per_video)
        print(f"   → Total textos recolectados: {len(all_texts)}")
        return all_texts

    if api is not None:
        all_texts = await _run(api)
    else:
        async with TikTokApi() as api:
            await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
            all_texts = await _run(api)

    print(f"\n🧠 Etapa 4: Analizando qué está funcionando para @{username}...")
    insights = analyze_competitor(username, all_texts)

    print("\n✅ Pipeline completado")
    print("=" * 50)
    print(json.dumps(insights, indent=2, ensure_ascii=False))

    return insights


if __name__ == "__main__":
    asyncio.run(run_pipeline("therock", video_count=2, comments_per_video=10, country=select_region()))

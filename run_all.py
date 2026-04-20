import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.session_config import create_sessions_with_retry, select_region

import services.pipeline_tiktok_hashtag as p_hashtag
import services.pipeline_tiktok_mapa_nicho as p_nicho
import services.pipeline_tiktok_cuenta as p_cuenta
import services.pipeline_tiktok_trending as p_trending
import services.pipeline_tiktok_validacion as p_validacion

load_dotenv()
ms_token = os.environ.get("ms_token", None)


async def main():
    country = select_region()
    print("🔌 Creando sesión compartida con TikTok...")
    async with TikTokApi() as api:
        await create_sessions_with_retry(api, ms_token, pipeline="run_all", country=country)
        print("✅ Sesión activa — corriendo pipelines\n")

        # --- Comenta/descomenta los pipelines que quieres correr ---

        await p_nicho.run_pipeline(
            nicho="suplementos deportivos",
            hashtags=["proteina", "creatina", "preworkout", "suplementosdeportivos"],
            videos_por_hashtag=2,
            comments_per_video=5,
            api=api,
        )

        await p_hashtag.run_pipeline(
            keyword="#nopuedobajardepeso",
            video_count=2,
            comments_per_video=5,
            api=api,
        )

        await p_cuenta.run_pipeline(
            username="therock",
            video_count=2,
            comments_per_video=5,
            api=api,
        )

        await p_trending.run_pipeline(
            video_count=2,
            comments_per_video=5,
            api=api,
        )

        await p_validacion.run_pipeline(
            keywords=["bajar de peso", "quemar grasa", "perder barriga"],
            video_count=2,
            comments_per_video=5,
            api=api,
        )


if __name__ == "__main__":
    asyncio.run(main())

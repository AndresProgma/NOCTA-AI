import asyncio
import os
import random

_TEST = os.getenv("TIKTOK_MODE", "production").lower() == "test"


async def delay_between_comments():
    # Pausa breve entre comentarios para simular lectura humana.
    t = random.uniform(0.5, 1.5) if _TEST else random.uniform(5, 10)
    await asyncio.sleep(t)


async def delay_between_videos():
    # Pausa entre videos para no disparar rate-limiting de TikTok.
    t = random.uniform(2, 4) if _TEST else random.uniform(30, 60)
    if not _TEST:
        print(f"   ⏳ Pausa entre videos: {t:.1f}s")
    await asyncio.sleep(t)


async def delay_long_pause():
    # Pausa larga periódica para romper el patrón de scraping continuo.
    t = random.uniform(3, 6) if _TEST else random.uniform(90, 120)
    if not _TEST:
        print(f"   🛑 Pausa larga (anti-detección): {t:.1f}s")
    await asyncio.sleep(t)


async def delay_retry():
    # Espera antes de reintentar cuando falla la obtención de comentarios.
    t = random.uniform(5, 10) if _TEST else random.uniform(60, 90)
    print(f"   🔁 Error detectado — esperando {t:.1f}s antes de continuar")
    await asyncio.sleep(t)


async def fetch_comments_safe(api, video_id: str, count: int) -> list[str]:
    # Obtiene comentarios de un video con hasta 3 reintentos; retorna lista vacía si todos fallan.
    for attempt in range(3):
        try:
            video = api.video(id=video_id)
            texts = []
            async for comment in video.comments(count=count):
                raw = comment.as_dict
                text = raw.get("text") or raw.get("comment") or raw.get("content") or ""
                if text:
                    texts.append(text)
                await delay_between_comments()
            return texts
        except Exception as e:
            print(f"   ⚠️  Error comentarios (intento {attempt + 1}/3): {e}")
            if attempt < 2:
                await delay_retry()
    return []


async def collect_texts_from_videos(api, videos: list[dict], comments_per_video: int) -> list[str]:
    # Recorre la lista de videos, agrega su descripción y extrae comentarios con delays anti-detección.
    all_texts = []
    for i, video in enumerate(videos):
        if video.get("descripcion"):
            all_texts.append(video["descripcion"])

        video_url = video.get("url", "")
        autor = video.get("autor", "")
        if video_url:
            print(f"   🔗 {video_url}")
        print(f"   💬 Video {i + 1}/{len(videos)}: obteniendo comentarios...")
        comments = await fetch_comments_safe(api, video["id"], comments_per_video)
        all_texts.extend(comments)
        print(f"   → {len(comments)} comentarios obtenidos")

        await delay_between_videos()

        if (i + 1) % random.randint(2, 3) == 0 and i + 1 < len(videos):
            await delay_long_pause()

    return all_texts

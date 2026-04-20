
from TikTokApi import TikTokApi
import asyncio
import os

ms_token = os.environ.get("ms_token", None) # token guardado en ms_token

"""TikTokApi solo puede acceder a contenido público. Si el video es privado, no se podrá acceder a él.


--Señales base = datos masivos, consistentes y disponibles siempre
--Señales secundarias = datos útiles pero incompletos o inestables



en estas funciones debo agregar compartidos de el usuario."""


async def get_trending_videos(api, count=5):
    videos_data = []

    print("\n🔥 TRENDING VIDEOS\n" + "="*50)

    i = 1
    async for video in api.trending.videos(count=count):
        data = video.as_dict

        video_info = {
            "id": data.get("id"),
            "descripcion": data.get("desc"),                                          # texto del video → análisis semántico central de Nocta
            "autor": data.get("author", {}).get("uniqueId"),
            "autor_verificado": data.get("author", {}).get("verified"),               # distinguir creadores vs usuarios comunes
            "autor_seguidores": data.get("author", {}).get("followerCount"),          # peso/influencia del creador
            "fecha_creacion": data.get("createTime"),                                 # temporalidad de la señal
            "duracion_seg": data.get("video", {}).get("duration"),                    # formato corto vs largo cambia tipo de consumo
            "likes": data.get("stats", {}).get("diggCount"),
            "views": data.get("stats", {}).get("playCount"),
            "comments": data.get("stats", {}).get("commentCount"),
            "shares": data.get("stats", {}).get("shareCount"),
            "guardados": data.get("stats", {}).get("collectCount"),                   # señal de intención alta → el usuario quiere volver a este contenido
            "hashtags": [h.get("hashtagName") for h in data.get("textExtra", []) if h.get("hashtagName")],  # temas y nichos activos
            "musica_titulo": data.get("music", {}).get("title"),                      # tendencias culturales ligadas al contenido
            "musica_artista": data.get("music", {}).get("authorName"),
        }

        videos_data.append(video_info)

        # 🔥 FORMATO BONITO EN CONSOLA
        print(f"\n🎥 VIDEO #{i}")
        print("-"*40)
        print(f"👤 Autor: {video_info['autor']}")
        print(f"📝 Descripción: {video_info['descripcion']}")
        print(f"✅ Verificado: {video_info['autor_verificado']} | 👥 Seguidores: {video_info['autor_seguidores']}")
        print(f"⏱️ Duración: {video_info['duracion_seg']}s | 📅 Creado: {video_info['fecha_creacion']}")
        print(f"❤️ Likes: {video_info['likes']}")
        print(f"👀 Views: {video_info['views']}")
        print(f"💬 Comentarios: {video_info['comments']}")
        print(f"🔄 Shares: {video_info['shares']}")
        print(f"🔖 Guardados: {video_info['guardados']}")
        print(f"🏷️ Hashtags: {', '.join(video_info['hashtags']) if video_info['hashtags'] else 'ninguno'}")
        print(f"🎵 Música: {video_info['musica_titulo']} — {video_info['musica_artista']}")

        i += 1

    print("\n" + "="*50)

    return videos_data

"""""
##comentarios de un video, se le pasa el id del video y devuelve los comentarios(toca darle un video id)
"""


async def get_comments():  
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )
        video = api.video(id=video_id)
        count = 0
        async for comment in video.comments(count=1):
            print(comment)
            print(comment.as_dict)

"""""
videos relacionados a un hashtag, se le pasa el nombre del hashtag 
y devuelve los videos relacionados a ese hashtag
"""
async def get_hashtag_videos():   
                                  
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )
        tag = api.hashtag(name="funny")
        async for video in tag.videos(count=30):
            print(video)
            print(video.as_dict)

""""
búsqueda de videos por palabra clave, se le pasa una palabra clave y devuelve los videos relacionados a esa palabra clave
"""
async def search_videos(api, keyword: str, count: int = 10) -> list[dict]:
    videos = []
    cursor = 0
    search_url = "https://www.tiktok.com/api/search/item/full/"

    while len(videos) < count:
        params = {
            "keyword": keyword,
            "count": 10,
            "cursor": cursor,
            "source": "search_video",
        }

        response = await api.make_request(url=search_url, params=params)

        if "item_list" in response:
            for video in response["item_list"]:
                videos.append({
                    "id": video.get("id"),
                    "descripcion": video.get("desc", ""),
                })
                if len(videos) >= count:
                    break

        has_more = response.get("has_more", False)
        cursor = response.get("cursor", 0)

        if not has_more:
            break

    return videos

async def user_example():
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )
        user = api.user("therock")
        user_data = await user.info()
        print(user_data)
        

        async for video in user.videos(count=30):
            print(video)
            print(video.as_dict)

        async for playlist in user.playlists():
            print(playlist)



async def get_video_example():
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )
        video = api.video(
            url="https://www.tiktok.com/@davidteathercodes/video/7074717081563942186"
        )

        async for related_video in video.related_videos(count=10):
            print(related_video)
            print(related_video.as_dict)

        video_info = await video.info()  # is HTML request, so avoid using this too much
        print(video_info)
        


async def get_videos_by_hashtag(api, hashtag: str, count: int = 10) -> list[dict]:
    # Itera el feed de un hashtag y extrae id, descripción y hashtags de cada video hasta el límite.
    videos = []
    tag = api.hashtag(name=hashtag)
    async for video in tag.videos(count=count):
        data = video.as_dict
        videos.append({
            "id": data.get("id"),
            "descripcion": data.get("desc", ""),
            "hashtags": [h.get("hashtagName") for h in data.get("textExtra", []) if h.get("hashtagName")],
        })
        if len(videos) >= count:
            break
    return videos


async def get_user_videos(api, username: str, count: int = 10) -> list[dict]:
    # Obtiene los últimos videos públicos de un perfil de TikTok hasta el límite indicado.
    videos = []
    user = api.user(username)
    async for video in user.videos(count=count):
        data = video.as_dict
        videos.append({
            "id": data.get("id"),
            "descripcion": data.get("desc", ""),
        })
        if len(videos) >= count:
            break
    return videos


async def get_comments_for_video(api, video_id: str, count: int = 20) -> list[str]:
    # Extrae el texto de los comentarios de un video dado su ID.
    video = api.video(id=video_id)
    texts = []
    async for comment in video.comments(count=count):
        raw = comment.as_dict
        print(f"   [DEBUG comentario raw]: {list(raw.keys())}")  # ver claves disponibles
        text = raw.get("text") or raw.get("comment") or raw.get("content") or ""
        if text:
            texts.append(text)
    return texts


async def main():
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=5,
            browser="webkit",
            headless=False
        )

        # 🔥 elige qué quieres ejecutar
        await get_trending_videos(api, count=3)

        # puedes probar otras también:
        # await user_example()
        # await get_video_example()


if __name__ == "__main__":
    asyncio.run(main())
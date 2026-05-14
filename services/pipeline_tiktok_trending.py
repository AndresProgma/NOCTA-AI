import asyncio
import os
import sys
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from TikTokApi import TikTokApi
from services.scraping import get_trending_videos
from services.analytics import analyze_signals, build_transcription_context
from services.session_config import create_sessions_with_retry, select_region, ask_transcription
from services.human_pace import fetch_comments_safe, delay_between_videos


class _Tee:
    # Duplica los writes de stdout a un archivo de log, para que el output se vea Y se guarde.
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
            except Exception:
                pass

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass

load_dotenv()
ms_token = os.environ.get("ms_token", None)

PIPELINE_NAME = "tiktok_trending"

"""Este pipeline accede al feed de contenido viral de TikTok sin filtro de nicho ni categoría. Analiza cada video
  individualmente: sus propios comentarios y transcripción, generando insights específicos por video.

  Para qué sirve a Nocta: Detectar tendencias emergentes antes de que se saturen, con contexto completo
  de lo que dice el creador y cómo responde su audiencia, video por video."""


async def run_pipeline(video_count: int = 2, comments_per_video: int = 10, api=None, country: str | None = None, transcribe: bool = False) -> dict:
    # Analiza cada video trending individualmente con sus propios comentarios y transcripción.
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_path = os.path.join(output_dir, f"trending_{timestamp}.txt")
    json_path = os.path.join(output_dir, f"trending_{timestamp}.json")

    _original_stdout = sys.stdout
    log_file = open(log_path, "w", encoding="utf-8")
    sys.stdout = _Tee(_original_stdout, log_file)

    def _finalize(result: dict) -> dict:
        sys.stdout = _original_stdout
        try:
            log_file.close()
        except Exception:
            pass
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"⚠️  No se pudo guardar JSON: {e}")
        print(f"\n💾 Output guardado en:")
        print(f"   📄 {log_path}")
        print(f"   🗃️  {json_path}")
        return result

    print(f"\n🚀 Iniciando pipeline de tendencias globales TikTok")
    print("=" * 50)

    proxy_hints = ["proxy", "tunnel", "bandwidth", "timeout", "connect", "remote", "browser", "playwright", "socket", "closed", "disconnected", "net::", "econnreset", "etimedout"]

    def _looks_like_proxy_failure(exc: Exception) -> bool:
        msg = (str(exc) + " " + type(exc).__name__).lower()
        return any(hint in msg for hint in proxy_hints)

    interrupted = {"flag": False}

    async def _run(api):
        resultados: dict = {}
        print(f"\n🔥 Etapa 1: Obteniendo {video_count} videos trending...")
        try:
            videos = await get_trending_videos(api, count=video_count)
        except Exception as e:
            print(f"   ❌ Falló la obtención de videos trending ({type(e).__name__}): {e}")
            print(f"   ⚠️  Probable agotamiento de proxy/bandwidth — sigo al ranking con lo que haya.")
            interrupted["flag"] = True
            return resultados
        print(f"   → {len(videos)} videos obtenidos")

        for i, video in enumerate(videos, 1):
            video_id = video.get("id")
            desc = (video.get("descripcion") or f"video_{video_id}")[:60]
            video_url = video.get("url", f"https://www.tiktok.com/@{video.get('autor', '')}/video/{video_id}")
            print(f"\n{'='*50}")
            print(f"🎥 VIDEO {i}/{len(videos)}: {desc}")
            print(f"🔗 {video_url}")
            print("=" * 50)

            try:
                texts = [video["descripcion"]] if video.get("descripcion") else []

                print(f"   💬 Obteniendo comentarios...")
                comments = await fetch_comments_safe(api, video_id, comments_per_video)
                texts.extend(comments)
                print(f"   → {len(comments)} comentarios obtenidos")

                video_context = ""
                if transcribe:
                    print(f"   🎙️  Transcribiendo video...")
                    try:
                        video_context = await build_transcription_context(api, [video])
                    except Exception as e_trans:
                        print(f"   ⚠️  Transcripción falló ({type(e_trans).__name__}): sigo solo con comentarios")
                    if video_context:
                        print(f"\n   📄 Transcripción:")
                        print("   " + "-" * 48)
                        print(video_context)
                        print("   " + "-" * 48)

                print(f"   🧠 Analizando señales del video...")
                insights = analyze_signals(desc, texts, video_context=video_context)
                print(json.dumps(insights, indent=2, ensure_ascii=False))
                resultados[video_id] = {"video": desc, "url": video_url, "insights": insights}

                if i < len(videos):
                    await delay_between_videos()
            except Exception as e:
                if _looks_like_proxy_failure(e):
                    print(f"\n⚠️  PROBABLE AGOTAMIENTO DE BANDWIDTH/PROXY en video {i} ({type(e).__name__}): {e}")
                    print(f"⚠️  Se procesaron {len(resultados)}/{len(videos)} videos antes del corte.")
                    print(f"⚠️  Salto al ranking final con lo que ya tenemos.\n")
                    interrupted["flag"] = True
                    break
                else:
                    print(f"\n⚠️  Error procesando video {i} ({type(e).__name__}): {e}")
                    print(f"⚠️  Sigo con el siguiente video.\n")
                    continue

        return resultados

    resultados = {}
    try:
        if api is not None:
            resultados = await _run(api)
        else:
            async with TikTokApi() as api:
                await create_sessions_with_retry(api, ms_token, pipeline=PIPELINE_NAME, country=country)
                resultados = await _run(api)
    except Exception as e:
        interrupted["flag"] = True
        if _looks_like_proxy_failure(e):
            print(f"\n⚠️  PROXY/BANDWIDTH AGOTADO antes/durante el scrape ({type(e).__name__}): {e}")
        else:
            print(f"\n⚠️  Error crítico durante el scrape ({type(e).__name__}): {e}")
        print(f"⚠️  Continuando al ranking con {len(resultados)} videos procesados.\n")

    if interrupted["flag"]:
        print(f"\n⚠️  Pipeline INTERRUMPIDO antes de completar — mostrando ranking con {len(resultados)} videos procesados")
    else:
        print("\n✅ Pipeline completado")
    print("=" * 60)

    if not resultados:
        print("\n⚠️  No se procesó ningún video. Sin ranking para mostrar.")
        print("=" * 60)
        return _finalize({"resultados": {}, "ranking_ids": [], "descartados_ids": [], "interrupted": interrupted["flag"]})

    def _val(data: dict, key: str) -> float:
        raw = data.get("insights", {}).get("scores", {}).get(key, {}).get("valor", 0.0)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _clasif(data: dict) -> dict:
        return data.get("insights", {}).get("clasificacion", {}) or {}

    def _comerciable(data: dict) -> bool:
        return bool(_clasif(data).get("comerciable", True))

    def _tipo(data: dict) -> str:
        return _clasif(data).get("tipo_contenido", "?")

    def _etiqueta(data: dict) -> str:
        # Determina cómo etiquetar el video: 💰 vendible, 🎬 contenido viral, o ambos.
        com = _comerciable(data)
        viral = _val(data, "potencial_contenido") >= 6.0
        if com and viral:
            return "💰🎬 VENDIBLE + VIRAL"
        if com:
            return "💰 VENDIBLE"
        if viral:
            return "🎬 CONTENIDO VIRAL"
        return "❌ DESCARTADO"

    DESCARTE_THRESHOLD = 4.0
    relevantes = {vid: d for vid, d in resultados.items() if _comerciable(d) or _val(d, "potencial_contenido") >= DESCARTE_THRESHOLD}
    descartados = {vid: d for vid, d in resultados.items() if vid not in relevantes}

    ranking = sorted(relevantes.items(), key=lambda x: _val(x[1], "potencial_tematica"), reverse=True)
    top_n = min(10, len(ranking))

    print(f"\n🏆 TOP {top_n} VIDEOS POR POTENCIAL (vendibles + contenido viral)")
    print("=" * 60)
    for i, (vid_id, data) in enumerate(ranking[:top_n], 1):
        insights = data.get("insights", {})
        pot = _val(data, "potencial_tematica")
        intc = _val(data, "intencion_compra")
        urg = _val(data, "urgencia_dolor")
        com_s = _val(data, "comerciabilidad")
        sat = _val(data, "saturacion_mercado")
        eng = _val(data, "relacion_comentarios")
        pcont = _val(data, "potencial_contenido")
        desc = data.get("video", "")[:80]
        url = data.get("url", "")
        tipo = _tipo(data)
        etiq = _etiqueta(data)
        audiencia = insights.get("audiencia", {}) or {}
        sentimiento = audiencia.get("sentimiento_dominante", "")
        psico = insights.get("analisis_psicologico", {}) or {}
        formato = insights.get("formato_viral", {}) or {}

        print(f"\n{i}. {etiq} | [{tipo}] {desc}")
        print(f"   🔗 {url}")
        print(f"   📊 potencial: {pot:.1f}  |  intención: {intc:.1f}  |  contenido: {pcont:.1f}  |  urgencia: {urg:.1f}  |  comerciab: {com_s:.1f}  |  saturación: {sat:.1f}  |  engagement: {eng:.1f}")
        if sentimiento:
            print(f"   🎭 sentimiento audiencia: {sentimiento}")

        disparadores = psico.get("disparadores_emocionales", []) or []
        razon_viral = psico.get("razon_viralidad", "")
        arquetipo = psico.get("arquetipo_narrativo", "")
        tension = psico.get("tension_central", "")
        if disparadores or razon_viral or arquetipo:
            print(f"   🧠 Psicología:")
            if disparadores:
                print(f"      disparadores: {', '.join(disparadores)}")
            if arquetipo:
                print(f"      arquetipo: {arquetipo}")
            if razon_viral:
                print(f"      por qué es viral: {razon_viral}")
            if tension:
                print(f"      tensión central: {tension}")

        tipo_formato = formato.get("tipo_formato", "")
        hook = formato.get("hook_detectado", "")
        patron = formato.get("patron_replicable", "")
        replic = formato.get("replicabilidad", "")
        if tipo_formato or hook or patron:
            print(f"   🎬 Formato viral:")
            if tipo_formato:
                print(f"      tipo: {tipo_formato}  |  replicabilidad: {replic}")
            if hook:
                print(f"      hook: {hook}")
            if patron:
                print(f"      patrón replicable: {patron}")

        propuestas = insights.get("propuestas_oferta", []) or []
        if propuestas:
            print(f"   💡 Ideas de oferta:")
            for p in propuestas[:2]:
                nombre = p.get("nombre_tentativo", "?")
                propuesta = p.get("propuesta_valor", "")
                precio = p.get("precio_sugerido", "?")
                print(f"      • {nombre} ({precio}) — {propuesta}")

    if descartados:
        print(f"\n🚫 DESCARTADOS (ni vendibles ni virales) ({len(descartados)})")
        print("=" * 60)
        for vid_id, data in descartados.items():
            tipo = _tipo(data)
            razon = _clasif(data).get("razon_no_comerciable", "")
            pcont = _val(data, "potencial_contenido")
            desc = data.get("video", "")[:60]
            print(f"   [{tipo}] {desc}  (contenido: {pcont:.1f})")
            if razon:
                print(f"      → {razon}")

    print("\n" + "=" * 60)
    return _finalize({
        "resultados": resultados,
        "ranking_ids": [vid for vid, _ in ranking],
        "descartados_ids": list(descartados.keys()),
        "interrupted": interrupted["flag"],
    })


if __name__ == "__main__":
    country = select_region()
    transcribe = ask_transcription()
    asyncio.run(run_pipeline(video_count=30, comments_per_video=15, country=country, transcribe=transcribe))

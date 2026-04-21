import os
import json
import tempfile
import yt_dlp
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def _is_useful_transcription(text: str) -> bool:
    # Descarta transcripciones de canciones/bailes: pocas palabras únicas o texto demasiado corto.
    if not text or not text.strip():
        return False
    words = text.strip().split()
    if len(words) < 25:
        return False
    # Si más del 60% de las palabras son repetidas, probablemente es una canción
    unique_ratio = len(set(w.lower() for w in words)) / len(words)
    if unique_ratio < 0.4:
        return False
    return True


def transcribe_from_bytes(video_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio,
                response_format="text",
            )
        return transcription
    finally:
        os.remove(tmp_path)


def _download_tiktok_audio(video_id: str, autor: str) -> str:
    # Descarga el audio de un video de TikTok con yt-dlp y retorna la ruta del archivo temporal.
    tmp_path = os.path.join(tempfile.gettempdir(), f"nocta_{video_id}")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": tmp_path,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.tiktok.com/@{autor}/video/{video_id}"])
    return tmp_path + ".mp3"


async def build_transcription_context(api, videos: list[dict]) -> str:
    transcripts = []
    for i, v in enumerate(videos, 1):
        video_id = v.get("id")
        if not video_id:
            continue
        audio_path = None
        try:
            print(f"   🎙️  Transcribiendo video {i}/{len(videos)} (id={video_id})...")
            autor = v.get("autor") or v.get("author", "tiktok")
            audio_path = _download_tiktok_audio(video_id, autor)
            with open(audio_path, "rb") as audio:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio,
                    response_format="text",
                )
            text = transcription.strip()
            desc = (v.get("descripcion") or "")[:80]
            transcripts.append(f"[VIDEO {i} — {desc}]\n{text}")
            print(f"      → {len(text)} caracteres transcritos")
        except Exception as e:
            print(f"   ⚠️  No se pudo transcribir video {video_id}: {e}")
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
    return "\n\n".join(transcripts)

def analyze_signals(topic: str, texts: list[str], video_context: str = "") -> dict:
    combined = "\n".join(f"- {t}" for t in texts if t and t.strip())

    has_transcription = _is_useful_transcription(video_context)
    if not has_transcription and video_context:
        print("   ⚠️  Transcripción descartada (canción/baile o muy corta) — análisis solo con comentarios")

    if has_transcription:
        sources_block = f"""
FUENTE PRIMARIA — TRANSCRIPCIÓN DEL VIDEO (lo que dice el creador; es tu fuente más importante):
{video_context}

FUENTE SECUNDARIA — COMENTARIOS DE LA AUDIENCIA (reacción al video):
{combined}
"""
        source_rule = "- Tienes DOS fuentes: la transcripción (creador) y los comentarios (audiencia). AMBAS son evidencia válida. Prioriza la transcripción para entender el mensaje; los comentarios para entender la reacción."
    else:
        sources_block = f"""
COMENTARIOS A ANALIZAR:
{combined}
"""
        source_rule = "- Analiza EXCLUSIVAMENTE los comentarios proporcionados."

    prompt = f"""Eres un analista de inteligencia de mercado. Tu única fuente de información son los textos que se te proporcionan a continuación.

REGLAS ESTRICTAS:
{source_rule}
- NO uses conocimiento externo, tendencias generales ni suposiciones propias.
- Si algo no está mencionado en los textos, NO lo incluyas.
- Cada punto del JSON debe poder rastrearse directamente a algo dicho en los textos.
- La evidencia debe ser una cita textual exacta tomada de la transcripción o de los comentarios. Indica la fuente entre paréntesis: (transcripción) o (comentario).

TEMA: "{topic}"
{sources_block}
Devuelve ÚNICAMENTE un JSON con esta estructura. Cada item debe ser un objeto con "insight" y "evidencia" (cita textual exacta + fuente):
{{
  "intenciones": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "fricciones": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "deseos_latentes": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "oportunidades": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "resumen": "resumen de 2-3 oraciones basado solo en los textos"
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def analyze_competitor(username: str, texts: list[str], video_context: str = "") -> dict:
    combined = "\n".join(f"- {t}" for t in texts if t and t.strip())

    has_transcription = _is_useful_transcription(video_context)
    if not has_transcription and video_context:
        print("   ⚠️  Transcripción descartada (canción/baile o muy corta) — análisis solo con comentarios")

    if has_transcription:
        sources_block = f"""
FUENTE PRIMARIA — TRANSCRIPCIÓN DE LOS VIDEOS DE @{username} (lo que dice el creador; es tu fuente más importante para entender su ángulo y promesa):
{video_context}

FUENTE SECUNDARIA — COMENTARIOS DE LA AUDIENCIA (reacción al contenido del creador):
{combined}
"""
        source_rule = f"- Tienes DOS fuentes: la transcripción de @{username} (creador) y los comentarios (audiencia). AMBAS son evidencia válida. Prioriza la transcripción para entender qué propone el creador; los comentarios para entender cómo responde su mercado."
    else:
        sources_block = f"""
COMENTARIOS A ANALIZAR:
{combined}
"""
        source_rule = "- Analiza EXCLUSIVAMENTE los comentarios proporcionados."

    prompt = f"""Eres un analista de inteligencia de mercado. Tu única fuente de información son los textos de @{username} en TikTok.

REGLAS ESTRICTAS:
{source_rule}
- NO uses conocimiento externo, tendencias generales ni suposiciones propias.
- Si algo no está mencionado en los textos, NO lo incluyas.
- Cada punto debe poder rastrearse directamente a algo dicho en los textos.
- La evidencia debe ser una cita textual exacta. Indica la fuente entre paréntesis: (transcripción) o (comentario).
{sources_block}
Devuelve ÚNICAMENTE un JSON con esta estructura. Cada item debe ser un objeto con "insight" y "evidencia" (cita textual exacta + fuente):
{{
  "dolores_deseos": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "prueba_social": {{
    "testimonios_detectados": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
    "perfiles_inesperados": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
    "resultados_mencionados": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}]
  }},
  "objeciones_vencidas": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "oportunidades": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "resumen": "resumen de 2-3 oraciones sobre qué está funcionando de este creador según su audiencia"
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)

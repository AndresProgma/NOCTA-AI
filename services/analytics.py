import os
import json
import tempfile
import yt_dlp
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


SCORING_RUBRIC = """
SCORES NUMÉRICOS (de 0.0 a 10.0, con un decimal). Cada score debe incluir una justificación breve (1 oración) citando la evidencia que lo sustenta:

1. intencion_compra: qué tan fuerte es la señal de que la audiencia compraría algo relacionado al tema.
   - 0-2: nadie expresa interés en comprar.
   - 3-4: curiosidad aislada, sin acción concreta.
   - 5-6: algunas preguntas tipo "¿dónde lo consigo?" o "link plis".
   - 7-8: múltiples pedidos de links, quejas por productos actuales que no funcionan, búsqueda activa de solución.
   - 9-10: demanda masiva sin solución existente, frustración generalizada por no encontrar dónde comprar.

2. relacion_comentarios: qué tan sustantiva es la conversación (calidad, no volumen).
   - 0-2: mayoritariamente emojis, "jaja", "real", reacciones vacías.
   - 3-4: comentarios cortos sin contenido relevante.
   - 5-6: mezcla equilibrada de ruido y sustantivos.
   - 7-8: mayoría con experiencia personal, preguntas, opiniones desarrolladas.
   - 9-10: conversaciones ricas entre usuarios, debates, historias completas.

3. comerciabilidad: qué tan vendible es realmente este ángulo/tema.
   - 0-2: contenido puramente entretenimiento, drama, política, baile, infantil — casi imposible de monetizar limpio.
   - 3-4: tiene alguna conexión comercial pero débil.
   - 5-6: ángulo comerciable estándar.
   - 7-8: claramente vendible, audiencia con poder adquisitivo y disposición.
   - 9-10: producto/servicio casi obvio, mercado pagador identificado.

4. urgencia_dolor: qué tan urgente es el dolor para la audiencia (cuándo lo resolvería).
   - 0-2: latente, no piensa todavía en resolverlo.
   - 3-4: crónico aceptado, "ya me acostumbré".
   - 5-6: crónico molesto, busca solución cuando se acuerda.
   - 7-8: agudo, busca solución activamente.
   - 9-10: dolor desesperado, pagaría hoy mismo.

5. saturacion_mercado: INVERTIDO. Alto = MENOS saturado = MÁS oportunidad. Bajo = MUY saturado.
   - 0-2: mercado saturadísimo, soluciones por todos lados (mencionan muchas marcas conocidas).
   - 3-4: saturado, ya hay soluciones aceptadas.
   - 5-6: ocupado pero hay huecos.
   - 7-8: poca competencia visible, soluciones débiles.
   - 9-10: nadie está sirviendo este dolor.

6. potencial_contenido: qué tan explotable es el FORMATO/ÁNGULO para crear contenido viral, INDEPENDIENTE de si hay producto detrás. Un video puede no vender nada y tener potencial_contenido 9 si el formato es altamente replicable y dispara emociones potentes (ej.: storytimes, confesiones, controversias, "señales de", revelaciones, listas, etc.).
   - 0-2: contenido único sin patrón, formato no replicable, sin gancho emocional claro.
   - 3-4: formato genérico, poca tracción esperada al replicarlo.
   - 5-6: formato decente pero saturado o poco diferenciado.
   - 7-8: formato viral identificable con disparadores emocionales claros, fácil de adaptar a otros nichos.
   - 9-10: formato altamente viral con múltiples disparadores psicológicos potentes (morbo, indignación, validación social, FOMO, curiosity gap), replicable en muchos contextos.

IMPORTANTE: NO devuelvas `potencial_tematica` — ese score se computa después en Python como promedio ponderado de los 6 anteriores.
"""

_SCORES_SCHEMA = """  "scores": {
    "intencion_compra": {"valor": 0.0, "justificacion": "..."},
    "relacion_comentarios": {"valor": 0.0, "justificacion": "..."},
    "comerciabilidad": {"valor": 0.0, "justificacion": "..."},
    "urgencia_dolor": {"valor": 0.0, "justificacion": "..."},
    "saturacion_mercado": {"valor": 0.0, "justificacion": "..."},
    "potencial_contenido": {"valor": 0.0, "justificacion": "..."}
  },"""

_PSICOLOGIA_SCHEMA = """  "analisis_psicologico": {
    "disparadores_emocionales": ["morbo | indignación | validación social | FOMO | miedo | esperanza | identificación | nostalgia | envidia | curiosidad | otros — usar varios si aplica"],
    "razon_viralidad": "explicación breve de por qué la gente ve hasta el final, comenta o comparte",
    "sesgos_cognitivos": ["curiosity gap | prueba social | controversy bias | autoridad | escasez | confirmación | otros"],
    "arquetipo_narrativo": "revelación | transformación | drama | victoria del débil | choque cultural | confesión | exposé | otro",
    "tension_central": "qué pregunta o duda queda en la cabeza del espectador",
    "audiencia_emocional": "qué busca emocionalmente la audiencia que consume esto (escape, validación, morbo, esperanza, etc.)"
  },"""

_FORMATO_SCHEMA = """  "formato_viral": {
    "tipo_formato": "storytime | revelación | controversia | lista | antes-después | tutorial | reacción | confesión | exposé | señales-de | duet-respuesta | otro",
    "hook_detectado": "qué dijo/hizo el creador en los primeros segundos para enganchar",
    "patron_replicable": "cómo se podría replicar este formato en otro nicho — fórmula concreta",
    "replicabilidad": "alta | media | baja"
  },"""

_CLASIFICACION_SCHEMA = """  "clasificacion": {
    "tipo_contenido": "educativo | producto | servicio | entretenimiento | baile | politica | drama | infantil | otro",
    "comerciable": true,
    "razon_no_comerciable": "solo si comerciable=false; si comerciable=true dejá string vacío"
  },"""

_AUDIENCIA_SCHEMA = """  "audiencia": {
    "perfil_inferido": "rango etario, género probable, nivel socioeconómico — inferido del lenguaje y temas",
    "jerga_caracteristica": ["frase real usada por la audiencia", "otra frase real"],
    "sentimiento_dominante": "frustración | esperanza | urgencia | escepticismo | curiosidad | enojo | otro"
  },"""

_MERCADO_SCHEMA = """  "mercado": {
    "soluciones_mencionadas": ["productos/marcas/herramientas citados, o [] si no hay"],
    "quejas_sobre_soluciones": ["qué dicen mal de lo que ya existe, o [] si no hay"],
    "urgencia_dolor_clasificacion": "aguda | cronica | latente",
    "barrera_entrada": "baja | media | alta"
  },"""

_PROPUESTAS_SCHEMA = """  "propuestas_oferta": [
    {
      "nombre_tentativo": "...",
      "propuesta_valor": "una frase que conecta con el dolor real detectado",
      "audiencia_target": "...",
      "precio_sugerido": "rango USD",
      "tipo": "producto físico | digital | servicio | suscripción"
    }
  ],"""


_POTENCIAL_WEIGHTS = {
    "intencion_compra": 0.22,
    "potencial_contenido": 0.20,
    "urgencia_dolor": 0.15,
    "comerciabilidad": 0.15,
    "relacion_comentarios": 0.15,
    "saturacion_mercado": 0.13,
}


def _compute_potencial(scores: dict) -> dict:
    def v(k: str) -> float:
        raw = scores.get(k, {}).get("valor", 0.0)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0
    total = sum(v(k) * w for k, w in _POTENCIAL_WEIGHTS.items())
    top_dim, top_w = max(_POTENCIAL_WEIGHTS.items(), key=lambda kw: v(kw[0]) * kw[1])
    return {
        "valor": round(total, 1),
        "justificacion": f"Composite ponderado de los 5 scores base. Dimensión que más aporta: {top_dim} ({v(top_dim):.1f} × {top_w}).",
    }


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
- Si algo no está mencionado en los textos, NO lo incluyas. Si un array no tiene contenido respaldado por evidencia, déjalo vacío [].
- Cada punto debe poder rastrearse directamente a algo dicho en los textos.
- La evidencia debe ser una cita textual exacta tomada de la transcripción o de los comentarios. Indica la fuente entre paréntesis: (transcripción) o (comentario).
- Los scores y campos blandos (audiencia, mercado) deben basarse EXCLUSIVAMENTE en la evidencia presente en los textos, no en suposiciones genéricas.
- Si el contenido NO es comerciable (entretenimiento puro, drama, política, baile, infantil), marcá `clasificacion.comerciable: false`, llená `razon_no_comerciable`, y los scores comerciales (`intencion_compra`, `urgencia_dolor`, `comerciabilidad`) deben quedar bajos (0-3). PERO aún así llená `analisis_psicologico` y `formato_viral` con todo el detalle posible — un video no-comerciable PUEDE tener altísimo `potencial_contenido` (ej.: storytimes, frutas infieles, confesiones).
- `propuestas_oferta` puede ser [] si el contenido no es comerciable.
- `analisis_psicologico` y `formato_viral` son OBLIGATORIOS para TODOS los videos, sean comerciables o no — son la base para detectar formatos virales replicables.

TEMA: "{topic}"
{sources_block}
{SCORING_RUBRIC}
Devuelve ÚNICAMENTE un JSON con esta estructura:
{{
{_CLASIFICACION_SCHEMA}
{_AUDIENCIA_SCHEMA}
{_MERCADO_SCHEMA}
{_PSICOLOGIA_SCHEMA}
{_FORMATO_SCHEMA}
  "intenciones": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "fricciones": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "deseos_latentes": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "oportunidades": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
{_PROPUESTAS_SCHEMA}
{_SCORES_SCHEMA}
  "resumen": "resumen de 2-3 oraciones basado solo en los textos"
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    if isinstance(result.get("scores"), dict):
        result["scores"]["potencial_tematica"] = _compute_potencial(result["scores"])
    return result


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
- Si algo no está mencionado en los textos, NO lo incluyas. Si un array no tiene contenido respaldado por evidencia, déjalo vacío [].
- Cada punto debe poder rastrearse directamente a algo dicho en los textos.
- La evidencia debe ser una cita textual exacta. Indica la fuente entre paréntesis: (transcripción) o (comentario).
- Los scores y campos blandos (audiencia, mercado) deben basarse EXCLUSIVAMENTE en la evidencia. Evaluá el ÁNGULO/NICHO que explota este creador, no a la cuenta como entidad.
- Si el contenido del creador NO es comerciable (entretenimiento puro, drama, política, baile, infantil), marcá `clasificacion.comerciable: false`, llená `razon_no_comerciable`, y los scores comerciales deben quedar bajos (0-3). PERO aún así llená `analisis_psicologico` y `formato_viral` con detalle — entender por qué funciona su contenido es clave aunque no venda.
- `propuestas_oferta` puede ser [] si no aplica.
- `analisis_psicologico` y `formato_viral` son OBLIGATORIOS — analizá qué hace que el contenido del creador conecte emocionalmente y qué patrón de formato usa.
{sources_block}
{SCORING_RUBRIC}
Devuelve ÚNICAMENTE un JSON con esta estructura:
{{
{_CLASIFICACION_SCHEMA}
{_AUDIENCIA_SCHEMA}
{_MERCADO_SCHEMA}
{_PSICOLOGIA_SCHEMA}
{_FORMATO_SCHEMA}
  "dolores_deseos": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "prueba_social": {{
    "testimonios_detectados": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
    "perfiles_inesperados": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
    "resultados_mencionados": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}]
  }},
  "objeciones_vencidas": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
  "oportunidades": [{{"insight": "...", "evidencia": "cita exacta [transcripción/comentario]"}}],
{_PROPUESTAS_SCHEMA}
{_SCORES_SCHEMA}
  "resumen": "resumen de 2-3 oraciones sobre qué está funcionando de este creador según su audiencia"
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    if isinstance(result.get("scores"), dict):
        result["scores"]["potencial_tematica"] = _compute_potencial(result["scores"])
    return result

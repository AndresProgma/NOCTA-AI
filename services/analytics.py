import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def analyze_signals(topic: str, texts: list[str]) -> dict:
    combined = "\n".join(f"- {t}" for t in texts if t and t.strip())

    prompt = f"""Eres un analista de inteligencia de mercado. Tu única fuente de información son los textos que se te proporcionan a continuación.

REGLAS ESTRICTAS:
- Analiza EXCLUSIVAMENTE los textos proporcionados. Nada más.
- NO uses conocimiento externo, tendencias generales ni suposiciones propias.
- Si algo no está mencionado en los textos, NO lo incluyas.
- Cada punto del JSON debe poder rastrearse directamente a algo dicho en los textos.

TEMA: "{topic}"

TEXTOS A ANALIZAR:
{combined}

Devuelve ÚNICAMENTE un JSON con esta estructura:
{{
  "intenciones": ["intenciones de compra o acción detectadas en los textos"],
  "fricciones": ["quejas, frustraciones o problemas mencionados en los textos"],
  "deseos_latentes": ["necesidades implícitas inferidas directamente de los textos"],
  "oportunidades": ["oportunidades basadas únicamente en lo que dicen los textos"],
  "resumen": "resumen de 2-3 oraciones basado solo en los textos"
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def analyze_competitor(username: str, texts: list[str]) -> dict:
    combined = "\n".join(f"- {t}" for t in texts if t and t.strip())

    prompt = f"""Eres un analista de inteligencia de mercado. Tu única fuente de información son los comentarios y descripciones de videos del creador @{username} en TikTok.

REGLAS ESTRICTAS:
- Analiza EXCLUSIVAMENTE los textos proporcionados. Nada más.
- NO uses conocimiento externo, tendencias generales ni suposiciones propias.
- Si algo no está mencionado en los textos, NO lo incluyas.
- Cada punto debe poder rastrearse directamente a algo dicho en los textos.

TEXTOS A ANALIZAR:
{combined}

Devuelve ÚNICAMENTE un JSON con esta estructura:
{{
  "dolores_deseos": ["dolores, frustraciones o deseos que expresa la audiencia"],
  "prueba_social": {{
    "testimonios_detectados": ["casos reales de éxito mencionados en comentarios"],
    "perfiles_inesperados": ["tipos de persona fuera del target obvio que reportan éxito"],
    "resultados_mencionados": ["resultados concretos que la gente dice haber obtenido"]
  }},
  "objeciones_vencidas": ["creencias o dudas que la audiencia tenía y superó"],
  "oportunidades": ["segmentos o ángulos detectados en los textos que podrían explotarse"],
  "resumen": "resumen de 2-3 oraciones sobre qué está funcionando de este creador según su audiencia"
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)

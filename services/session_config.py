import os
import random
from datetime import datetime
from urllib.parse import urlparse

REGIONES = {
    "1":  ("México",              "MX"),
    "2":  ("Colombia",            "CO"),
    "3":  ("Argentina",           "AR"),
    "4":  ("España",              "ES"),
    "5":  ("Estados Unidos",      "US"),
    "6":  ("Perú",                "PE"),
    "7":  ("Chile",               "CL"),
    "8":  ("Venezuela",           "VE"),
    "9":  ("Todas (rotación)",    None),
}

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "proxy_log.txt")


def select_region() -> str | None:
    # Muestra menú interactivo y retorna el código ISO del país elegido, o None para rotación libre.
    print("\n🌎 Selecciona la región para el proxy:")
    for key, (nombre, codigo) in REGIONES.items():
        flag = f"[{codigo}]" if codigo else "[ALL]"
        print(f"   {key}. {flag} {nombre}")

    while True:
        opcion = input("\n→ Elige una opción (1-9): ").strip()
        if opcion in REGIONES:
            nombre, codigo = REGIONES[opcion]
            print(f"   ✅ Región seleccionada: {nombre}\n")
            return codigo
        print("   Opción inválida, intenta de nuevo.")


def ask_transcription() -> bool:
    # Pregunta al usuario si quiere transcribir los videos con Whisper antes de analizar.
    print("\n🎙️  ¿Quieres transcribir los videos para usarlos como contexto?")
    print("   (Consume bandwidth del proxy y tiempo extra, pero mejora los insights)")
    while True:
        opcion = input("   → s/n: ").strip().lower()
        if opcion in ("s", "si", "sí", "y", "yes"):
            print("   ✅ Transcripción ACTIVADA\n")
            return True
        if opcion in ("n", "no"):
            print("   ⏭️  Transcripción desactivada\n")
            return False
        print("   Opción inválida, escribe s o n.")


def _log(proxy_server: str, status: str, pipeline: str = ""):
    # Escribe una línea timestamped en proxy_log.txt con el estado del proxy (USADO/OK/BLOCKED).
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {status:<8} | {proxy_server:<45} | {pipeline}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"[LOG] {line.strip()}")


def log_proxy_ok(proxy_server: str, pipeline: str = ""):
    # Registra que el proxy completó la sesión sin errores.
    _log(proxy_server, "OK", pipeline)


def log_proxy_blocked(proxy_server: str, pipeline: str = ""):
    # Registra que el proxy fue rechazado por TikTok o falló la conexión.
    _log(proxy_server, "BLOCKED", pipeline)


def _parse_proxy_url(url: str) -> dict:
    # Convierte una URL de proxy (http://user:pass@host:port) al dict que espera Playwright.
    parsed = urlparse(url)
    proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


def _apply_country(proxy: dict, country: str | None) -> dict:
    # Reescribe el username de Webshare para fijar un país: base-PAISES-N → base-COUNTRY-N.
    if not country or "username" not in proxy:
        return proxy
    parts = proxy["username"].split("-")
    base = parts[0]
    numero = parts[-1]
    proxy["username"] = f"{base}-{country}-{numero}"
    return proxy


def _load_proxies(country: str | None = None) -> list[dict]:
    # Lee PROXY_LIST (múltiples) o PROXY_SERVER (uno) del .env y aplica el filtro de país.
    proxy_list = os.getenv("PROXY_LIST", "").strip()
    if proxy_list:
        proxies = []
        for entry in proxy_list.split(","):
            entry = entry.strip()
            if entry:
                proxies.append(_apply_country(_parse_proxy_url(entry), country))
        return proxies

    proxy_server = os.getenv("PROXY_SERVER", "").strip()
    if proxy_server:
        proxy = _parse_proxy_url(proxy_server)
        user = os.getenv("PROXY_USERNAME", "").strip()
        pwd = os.getenv("PROXY_PASSWORD", "").strip()
        if user:
            proxy["username"] = user
        if pwd:
            proxy["password"] = pwd
        return [_apply_country(proxy, country)]

    return []


def _base_session_config(ms_token: str) -> dict:
    # Arma el dict base que se pasa a TikTokApi.create_sessions(); bloquea recursos pesados para ahorrar bandwidth.
    return {
        "ms_tokens": [ms_token],
        "num_sessions": 1,
        "sleep_after": random.uniform(5, 9),
        "browser": os.getenv("TIKTOK_BROWSER", "chromium"),
        "headless": os.getenv("TIKTOK_HEADLESS", "true").lower() != "false",
        "timeout": int(os.getenv("TIKTOK_TIMEOUT", "90000")),
        "suppress_resource_load_types": ["image", "media", "font", "stylesheet"],
    }


def build_session_config(ms_token: str, pipeline: str = "") -> dict:
    # Construye config eligiendo un proxy aleatorio de la lista; usado cuando no se necesita retry.
    config = _base_session_config(ms_token)

    proxies = _load_proxies()
    if proxies:
        proxy = random.choice(proxies)
        config["proxies"] = [proxy]
        config["_proxy_server"] = proxy["server"]
        _log(proxy["server"], "USADO", pipeline)
    else:
        print("[CONFIG] Sin proxy — conexión directa")

    return config


async def create_sessions_with_retry(api, ms_token: str, pipeline: str = "", country: str | None = None) -> str | None:
    # Shufflea todos los proxies disponibles e intenta cada uno hasta que uno abra TikTok con éxito.
    proxies = _load_proxies(country=country)

    if not proxies:
        print("[CONFIG] Sin proxy — conexión directa")
        config = _base_session_config(ms_token)
        await api.create_sessions(**config)
        return None

    random.shuffle(proxies)
    last_error = None

    for proxy in proxies:
        config = _base_session_config(ms_token)
        config["proxies"] = [proxy]
        server = proxy["server"]
        _log(server, "USADO", pipeline)
        try:
            await api.create_sessions(**config)
            log_proxy_ok(server, pipeline)
            return server
        except Exception as e:
            log_proxy_blocked(server, pipeline)
            last_error = e

    raise RuntimeError(f"Todos los proxies fallaron. Último error: {last_error}") from last_error

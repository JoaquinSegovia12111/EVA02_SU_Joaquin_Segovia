#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
eva02_segovia_graphhopper.py
Mejora del Software de Geolocalización con Python (GraphHopper)

Requisitos:
  pip install requests

Ejecución:
  python3 eva02_segovia_graphhopper.py

Características:
- Prompts y mensajes en español
- Salir con 's' o 'salir' en cualquier prompt
- Números con máximo dos decimales
- Instrucciones paso a paso en español (locale=es)
- Viaje desde "tu casa" hacia "la sede"
"""

import os
import sys
import requests
import urllib.parse
from typing import Tuple, Dict, Any, Optional

GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL   = "https://graphhopper.com/api/1/route?"
# Tu API Key (ya incluida):
DEFAULT_API_KEY = "65975508-0ef0-4071-b644-1fbd519dedf9"

PERFILES_VALIDOS = {"car", "bike", "foot"}  # car=auto, bike=bicicleta, foot=a pie


def salir_si_corresponde(txt: str) -> bool:
    return txt.strip().lower() in {"s", "salir"}


def obtener_api_key() -> str:
    key = os.getenv("GRAPHHOPPER_API_KEY", "").strip()
    return key if key else DEFAULT_API_KEY


def geocodificar(direccion: str, key: str) -> Tuple[int, Optional[float], Optional[float], str]:
    direccion = (direccion or "").strip()
    while direccion == "":
        direccion = input("⚠️  La dirección no puede ser vacía. Escribe nuevamente: ").strip()
        if salir_si_corresponde(direccion):
            print("Saliendo…")
            sys.exit(0)

    params = {"q": direccion, "limit": "1", "key": key}
    url = GEOCODE_URL + urllib.parse.urlencode(params)

    try:
        resp = requests.get(url, timeout=20)
        status = resp.status_code
        data = resp.json()
    except Exception as exc:
        print(f"[Geocodificación] Error de red/parseo: {exc}")
        return 0, None, None, direccion

    if status == 200 and isinstance(data, dict) and len(data.get("hits", [])) > 0:
        hit = data["hits"][0]
        lat = hit["point"]["lat"]
        lng = hit["point"]["lng"]

        nombre = hit.get("name", direccion)
        pais = hit.get("country", "")
        region = hit.get("state", "")
        tipo = hit.get("osm_value", "")

        if region and pais:
            etiqueta = f"{nombre}, {region}, {pais}"
        elif pais:
            etiqueta = f"{nombre}, {pais}"
        else:
            etiqueta = nombre

        print(f"\n📍 Geocodificado: {etiqueta} (tipo: {tipo})")
        print(f"   URL geocodificación: {url}\n")
        return status, float(lat), float(lng), etiqueta

    msg = data.get("message") if isinstance(data, dict) else None
    if msg:
        print(f"[Geocodificación] estado={status} | mensaje: {msg}")
    else:
        print(f"[Geocodificación] estado={status} | sin resultados para: {direccion}")

    return status, None, None, direccion


def formatear_duracion_ms(ms: int) -> str:
    seg_total = ms // 1000
    h = seg_total // 3600
    m = (seg_total % 3600) // 60
    s = seg_total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def rutear(origen: Tuple[float, float],
           destino: Tuple[float, float],
           key: str,
           vehiculo: str = "car") -> Dict[str, Any]:
    op = f"&point={origen[0]}%2C{origen[1]}"
    dp = f"&point={destino[0]}%2C{destino[1]}"
    params = {"key": key, "vehicle": vehiculo, "locale": "es"}
    base = ROUTE_URL + urllib.parse.urlencode(params) + op + dp

    print("🛣️  URL de ruteo:")
    print(base)
    print("=" * 60)

    try:
        resp = requests.get(base, timeout=30)
        status = resp.status_code
        data = resp.json()
    except Exception as exc:
        return {"error": f"Error de red/parseo: {exc}"}

    if status != 200:
        return {"error": data.get("message", f"HTTP {status}")}

    return data


def imprimir_resumen(paths_data: Dict[str, Any], etiqueta_origen: str, etiqueta_destino: str, vehiculo: str):
    path = paths_data["paths"][0]
    dist_m = float(path["distance"])
    tiempo_ms = int(path["time"])

    km = dist_m / 1000.0
    millas = km / 1.61

    print(f"🚗 Indicaciones desde {etiqueta_origen} hasta {etiqueta_destino} en {vehiculo}")
    print("=" * 60)
    print(f"Distancia: {km:.2f} km / {millas:.2f} millas")
    print(f"Duración:  {formatear_duracion_ms(tiempo_ms)}")
    print("=" * 60)


def imprimir_paso_a_paso(paths_data: Dict[str, Any]):
    instrucciones = paths_data["paths"][0].get("instructions", [])
    if not instrucciones:
        print("No hay instrucciones paso a paso disponibles.")
        return

    print("🧭 Narrativa del viaje (paso a paso):")
    print("=" * 60)
    for paso in instrucciones:
        texto = paso.get("text", "")
        dist_m = float(paso.get("distance", 0.0))
        km = dist_m / 1000.0
        millas = km / 1.61
        print(f"- {texto} ({km:.2f} km / {millas:.2f} millas)")
    print("=" * 60)


def pedir(texto: str) -> str:
    valor = input(texto).strip()
    if salir_si_corresponde(valor):
        print("Saliendo…")
        sys.exit(0)
    return valor


def main():
    api_key = obtener_api_key()
    if not api_key or len(api_key) < 10:
        api_key = pedir("🔑 Escribe tu API Key de GraphHopper: ")

    print("\n=== Configuración del viaje (casa ➜ sede) ===")
    print("Puedes salir en cualquier momento escribiendo 's' o 'salir'.\n")

    print("Perfiles disponibles: car (auto), bike (bicicleta), foot (a pie)")
    vehiculo = pedir("Elige un perfil (car/bike/foot) [por defecto: car]: ").lower()
    if vehiculo not in PERFILES_VALIDOS:
        vehiculo = "car"

    casa = pedir("Dirección de tu casa: ")
    sede = pedir("Dirección de la sede: ")

    s1, lat1, lng1, etq1 = geocodificar(casa, api_key)
    s2, lat2, lng2, etq2 = geocodificar(sede, api_key)

    print("=" * 60)
    if s1 == 200 and s2 == 200 and lat1 is not None and lat2 is not None:
        datos = rutear((lat1, lng1), (lat2, lng2), api_key, vehiculo)
        if "error" in datos:
            print("❌ Error en el ruteo:", datos["error"])
            print("*" * 60)
            sys.exit(1)

        print("✅ Estado de la API de ruteo: 200")
        imprimir_resumen(datos, etq1, etq2, vehiculo)
        imprimir_paso_a_paso(datos)
    else:
        print("❌ No fue posible geocodificar una o ambas direcciones. Intenta nuevamente.")
        print("*" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
        sys.exit(0)

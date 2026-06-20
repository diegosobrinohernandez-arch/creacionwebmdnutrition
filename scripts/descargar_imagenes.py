#!/usr/bin/env python3
"""
Descarga todas las imagenes de md_nutrition_imagenes.json y las guarda
localmente en una carpeta organizada por marca. Al terminar, genera
md_nutrition_imagenes_local.json con las rutas locales en vez de URLs externas.

Uso:
    pip install requests slugify
    python3 descargar_imagenes.py md_nutrition_imagenes.json ./imagenes_md_nutrition

Requiere conexion a internet (no funciona dentro de este sandbox).
"""
import json, os, sys, time, re
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    sys.exit("Falta 'requests'. Instala con: pip install requests")


def slugify(text, maxlen=80):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:maxlen] or "producto"


def ext_from_url(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return ext
    return ".jpg"


def download(url, dest, retries=3, timeout=20):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MDNutritionBot/1.0)"}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return True
        except Exception as e:
            print(f"  intento {attempt}/{retries} fallo para {url}: {e}")
            time.sleep(1.5 * attempt)
    return False


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 descargar_imagenes.py md_nutrition_imagenes.json [carpeta_salida]")

    src_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("imagenes_md_nutrition")
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(src_path.read_text(encoding="utf-8"))
    productos = data["productos_con_imagen"]

    ok, fail = 0, 0
    fallidos = []

    for p in productos:
        marca_dir = out_dir / slugify(p["marca"])
        marca_dir.mkdir(parents=True, exist_ok=True)
        slug = slugify(p["titulo_csv"])

        local_images = []
        for i, url in enumerate(p["imagenes"]):
            ext = ext_from_url(url)
            fname = f"{slug}{'' if i == 0 else f'-{i+1}'}{ext}"
            dest = marca_dir / fname
            if dest.exists():
                ok += 1
                local_images.append(str(dest.as_posix()))
                continue
            print(f"Descargando: {p['marca']} / {p['titulo_csv']} ({i+1}/{len(p['imagenes'])})")
            if download(url, dest):
                ok += 1
                local_images.append(str(dest.as_posix()))
            else:
                fail += 1
                fallidos.append({"marca": p["marca"], "titulo_csv": p["titulo_csv"], "url": url})

        p["imagenes_local"] = local_images
        p["imagen_principal_local"] = local_images[0] if local_images else ""

    out_json = src_path.with_name(src_path.stem + "_local.json")
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nListo. Descargadas/OK: {ok}  |  Fallidas: {fail}")
    print(f"Imagenes en: {out_dir.resolve()}")
    print(f"JSON actualizado: {out_json.resolve()}")

    if fallidos:
        fail_path = out_dir / "_fallidos.json"
        fail_path.write_text(json.dumps(fallidos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Lista de fallos guardada en: {fail_path}")


if __name__ == "__main__":
    main()

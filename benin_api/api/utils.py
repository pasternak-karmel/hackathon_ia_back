"""
Utilitaires pour l'extraction des coordonnées des levés topographiques béninois
Utilise ton code qui marche avec Langchain + Google Gemini
"""

import os
import base64
import fitz  # PyMuPDF
from PIL import Image
import io
import tempfile
import requests
from urllib.parse import urlparse
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage


def png_to_base64_uri(image_path: str) -> str:
    """
    Convertit une image PNG en URI base64 (data:image/png;base64,...).
    """
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def pil_image_to_data_uri(image: Image.Image) -> str:
    """
    Convertit une image PIL en URI base64
    """
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def pdf_to_images(pdf_path: str, zoom: int = 4) -> list:
    """
    Convertit un PDF en images
    """
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images

def is_supported_extension(filename: str) -> bool:
    """Vérifie l'extension supportée"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in {'.png', '.jpg', '.jpeg', '.pdf'}

def infer_extension_from_content_type(content_type: str) -> str:
    """Déduit l'extension à partir du Content-Type"""
    mapping = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'application/pdf': '.pdf',
    }
    return mapping.get(content_type.split(';')[0].strip(), '')

def download_file_from_url(url: str, max_size_bytes: int = 50 * 1024 * 1024) -> str:
    """
    Télécharge un fichier depuis une URL HTTP(S) vers un fichier temporaire sécurisé.
    Valide la taille et le type de contenu.

    Returns: chemin du fichier temporaire
    """
    # Valider schéma URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL invalide: seulement http/https sont supportés")

    # Tenter de récupérer les headers d'abord
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()

        content_type = r.headers.get('Content-Type', '').lower()
        content_length = r.headers.get('Content-Length')

        # Déduire extension
        ext = os.path.splitext(parsed.path)[1].lower()
        if not is_supported_extension(ext):
            # Essayer avec le content-type
            ext = infer_extension_from_content_type(content_type)

        if ext not in {'.png', '.jpg', '.jpeg', '.pdf'}:
            raise ValueError(f"Type de contenu non supporté: {content_type or 'inconnu'}")

        # Vérifier taille si connue
        if content_length is not None:
            try:
                size = int(content_length)
                if size > max_size_bytes:
                    raise ValueError(f"Fichier trop volumineux ({size} > {max_size_bytes} octets)")
            except ValueError:
                pass

        # Télécharger par flux dans un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    downloaded += len(chunk)
                    if downloaded > max_size_bytes:
                        tmp.close()
                        os.unlink(tmp.name)
                        raise ValueError("Fichier trop volumineux pendant le téléchargement")
                    tmp.write(chunk)
            return tmp.name


def get_coordinates(file_path: str):
    """
    Get the coordinates from the file

    Args:
        file_path(str) : File path

    Returns:
      str : Return the coordinates
    """
    # Récupération de la clé api
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY non trouvée dans les variables d'environnement")

    # Initialisation du model
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", api_key=api_key)

    # Traitement images .png
    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Extrait moi les coordonnées et renvoi moi juste une liste de dict sous ce format : [{'x': 321562.2, 'y': 1135517.34}, {'x': 321590.39, 'y': 1135506.9}, etc...]",
                },
                {"type": "image_url", "image_url": png_to_base64_uri(file_path)},
            ]
        )
        result = llm.invoke([message])
        return result

    # Traitement pdf
    elif file_path.lower().endswith(".pdf"):
        images = pdf_to_images(file_path)
        base_64 = pil_image_to_data_uri(images[0])

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Extrait moi les coordonnées et renvoi moi juste une liste de dict sous ce format :  [{'x': 321562.2, 'y': 1135517.34}, {'x': 321590.39, 'y': 1135506.9}, etc...]",
                },
                {"type": "image_url", "image_url": base_64},
            ]
        )
        result = llm.invoke([message])
        return result
    
    else:
        raise ValueError("Format de fichier non supporté. Utilisez PNG, JPG, JPEG ou PDF.")


def parse_coordinates_response(response_content: str) -> list:
    """
    Parse la réponse de Gemini pour extraire les coordonnées
    
    Args:
        response_content: Contenu de la réponse de Gemini
        
    Returns:
        Liste de dictionnaires avec les coordonnées
    """
    import json
    import re
    
    try:
        # Nettoyer la réponse
        content = response_content.strip()
        
        # Enlever les balises markdown si présentes
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        # Essayer de parser directement en JSON
        try:
            coordinates = json.loads(content)
            if isinstance(coordinates, list):
                return coordinates
        except json.JSONDecodeError:
            pass
        
        # Fallback: chercher avec regex
        pattern = r"\{'x':\s*([\d.]+),\s*'y':\s*([\d.]+)\}"
        matches = re.findall(pattern, content)
        
        coordinates = []
        for match in matches:
            try:
                x = float(match[0])
                y = float(match[1])
                coordinates.append({"x": x, "y": y})
            except ValueError:
                continue
        
        return coordinates
        
    except Exception as e:
        print(f"Erreur parsing coordonnées: {e}")
        return []


def validate_benin_coordinates(coordinates: list) -> dict:
    """
    Valide que les coordonnées sont plausibles pour le Bénin
    
    Args:
        coordinates: Liste de coordonnées [{"x": ..., "y": ...}, ...]
        
    Returns:
        Dict avec résultats de validation
    """
    # Plages valides pour le Bénin (UTM 31N)
    benin_x_range = (390000, 430000)
    benin_y_range = (650000, 1300000)
    
    valid_coords = []
    invalid_coords = []
    
    for coord in coordinates:
        try:
            x = float(coord.get('x', 0))
            y = float(coord.get('y', 0))
            
            if (benin_x_range[0] <= x <= benin_x_range[1] and
                benin_y_range[0] <= y <= benin_y_range[1]):
                valid_coords.append(coord)
            else:
                invalid_coords.append(coord)
                
        except (ValueError, TypeError):
            invalid_coords.append(coord)
    
    return {
        "valid_coordinates": valid_coords,
        "invalid_coordinates": invalid_coords,
        "total_extracted": len(coordinates),
        "valid_count": len(valid_coords),
        "invalid_count": len(invalid_coords),
        "success_rate": len(valid_coords) / len(coordinates) * 100 if coordinates else 0
    }

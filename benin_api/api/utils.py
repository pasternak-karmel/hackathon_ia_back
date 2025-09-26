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
from urllib.parse import urlparse, quote, unquote
from google import genai


def calculate_centroid(coordinates):
    """
    Calcule le centroïde (centre géométrique) d'une liste de coordonnées
    
    Args:
        coordinates (list): Liste de dictionnaires avec clés 'x' et 'y'
        
    Returns:
        dict: Coordonnées du centroïde {'x': float, 'y': float} ou None si liste vide
    """
    if not coordinates:
        return None
    
    total_x = sum(coord['x'] for coord in coordinates)
    total_y = sum(coord['y'] for coord in coordinates)
    count = len(coordinates)
    
    return {
        "x": round(total_x / count, 2),
        "y": round(total_y / count, 2)
    }


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
        'application/octet-stream': '',  # Accepter octet-stream (GitHub utilise ça pour les PDFs)
    }
    return mapping.get(content_type.split(';')[0].strip(), '')

def convert_github_url_to_raw(url: str) -> str:
    """
    Convertit une URL GitHub blob vers une URL raw pour accès direct au fichier
    Gère aussi l'encodage correct des noms de fichiers avec espaces et évite le double encodage
    """
    if "github.com" in url and "/blob/" in url:
        # Convertir https://github.com/user/repo/blob/branch/file vers https://raw.githubusercontent.com/user/repo/branch/file
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        
        # Parser l'URL pour gérer correctement l'encodage
        parsed = urlparse(url)
        # Séparer le chemin en parties
        path_parts = parsed.path.split('/')
        if len(path_parts) >= 4:  # /user/repo/branch/filename...
            # Décoder d'abord le nom de fichier pour éviter le double encodage
            filename = path_parts[-1]
            # Décoder plusieurs fois si nécessaire (pour gérer le double encodage)
            decoded_filename = filename
            # Décoder jusqu'à ce qu'il n'y ait plus de changement
            while True:
                new_decoded = unquote(decoded_filename)
                if new_decoded == decoded_filename:
                    break
                decoded_filename = new_decoded
            # Re-encoder proprement une seule fois
            encoded_filename = quote(decoded_filename, safe='.-_')
            path_parts[-1] = encoded_filename
            # Reconstruire le chemin
            new_path = '/'.join(path_parts)
            url = f"{parsed.scheme}://{parsed.netloc}{new_path}"
    
    return url

def download_file_from_url(url: str, max_size_bytes: int = 50 * 1024 * 1024) -> str:
    """
    Télécharge un fichier depuis une URL HTTP(S) vers un fichier temporaire sécurisé.
    Valide la taille et le type de contenu.
    Convertit automatiquement les URLs GitHub blob vers raw.

    Returns: chemin du fichier temporaire
    """
    # Convertir URL GitHub si nécessaire
    url = convert_github_url_to_raw(url)
    
    # Valider schéma URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL invalide: seulement http/https sont supportés")

    # Tenter de récupérer les headers d'abord
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()

        content_type = r.headers.get('Content-Type', '').lower()
        content_length = r.headers.get('Content-Length')

        # Déduire extension depuis l'URL
        ext = os.path.splitext(parsed.path)[1].lower()
        
        # Si l'extension de l'URL est supportée, l'utiliser
        if is_supported_extension(ext):
            # Extension valide trouvée dans l'URL
            pass
        else:
            # Essayer avec le content-type
            ext_from_content = infer_extension_from_content_type(content_type)
            if ext_from_content:
                ext = ext_from_content
            elif content_type == 'application/octet-stream':
                # GitHub utilise octet-stream, essayer de deviner depuis l'URL
                if any(x in parsed.path.lower() for x in ['.pdf', '.png', '.jpg', '.jpeg']):
                    # Garder l'extension de l'URL même si pas reconnue initialement
                    pass
                else:
                    raise ValueError(f"Impossible de déterminer le type de fichier depuis l'URL: {parsed.path}")
            else:
                raise ValueError(f"Type de contenu non supporté: {content_type or 'inconnu'}")

        # Vérification finale
        if ext and ext not in {'.png', '.jpg', '.jpeg', '.pdf'}:
            raise ValueError(f"Extension de fichier non supportée: {ext}")

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
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY ou GEMINI_API_KEY non trouvée dans les variables d'environnement")

    # Configuration de l'API key et initialisation du client
    os.environ["GEMINI_API_KEY"] = api_key
    client = genai.Client()
    model_name = "gemini-2.5-flash"

    # Traitement images .png
    if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
        # Charger l'image
        from PIL import Image
        img = Image.open(file_path)
        
        prompt = """Extrait les coordonnées des bornes de ce levé topographique et retourne-les au format JSON valide.
                    
Format de réponse attendu (JSON avec guillemets doubles) :
[
  {"x": 321562.2, "y": 1135517.34},
  {"x": 321590.39, "y": 1135506.9}
]

IMPORTANT: Utilise uniquement des guillemets doubles (") pour le JSON, pas de guillemets simples (')."""
        
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, img]
        )
        
        # Créer un objet similaire à la réponse langchain pour compatibilité
        class MockResponse:
            def __init__(self, text):
                self.content = text
        
        return MockResponse(response.text)

    # Traitement pdf
    elif file_path.lower().endswith(".pdf"):
        images = pdf_to_images(file_path)
        
        prompt = "Extrait moi les coordonnées et renvoi moi juste une liste de dict sous ce format :  [{'x': 321562.2, 'y': 1135517.34}, {'x': 321590.39, 'y': 1135506.9}, etc...]"
        
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, images[0]]
        )
        
        # Créer un objet similaire à la réponse langchain pour compatibilité
        class MockResponse:
            def __init__(self, text):
                self.content = text
        
        return MockResponse(response.text)
    
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
            # Essayer de convertir les guillemets simples en guillemets doubles
            try:
                # Remplacer les guillemets simples par des guillemets doubles pour JSON valide
                content_fixed = content.replace("'", '"')
                coordinates = json.loads(content_fixed)
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

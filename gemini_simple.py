#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extraction des coordonnées des levés topographiques béninois avec Gemini
Inspiré de hackatonia.py mais avec l'API Gemini au lieu d'Ollama
"""

import os
import json
from pathlib import Path
from PIL import Image
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# === CONFIGURATION ===
INPUT_FOLDER = "Testing Data"  # Dossier où se trouvent les images de levés
OUTPUT_FOLDER = "Results"      # Sauvegarde des résultats
OUTPUT_CSV = "submission.csv"  # Fichier final

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === OCR avec Gemini (comme ollama dans hackatonia.py) ===
def ocr_image_gemini(img: Image.Image, api_key: str) -> str:
    """Extrait le texte d'une image avec Gemini (équivalent ocr_image_ollama)"""
    try:
        import google.generativeai as genai
    except ImportError:
        os.system("pip install google-generativeai")
        import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    response = model.generate_content([
        """Extract all visible text from this scanned image of a topographic survey.
        Preserve original formatting as much as possible.
        Return only the extracted text — no explanations, no introductions.
        Focus especially on coordinate tables with points P1, P2, P3... and their X, Y coordinates.
        If you encounter tables, format them clearly.""",
        img
    ])
    
    return response.text

# === Extraction coordonnées avec Gemini (comme check_ollama) ===
def extract_coordinates_gemini(text: str, api_key: str) -> str:
    """Extrait les coordonnées du texte avec Gemini (équivalent check_ollama)"""
    try:
        import google.generativeai as genai
    except ImportError:
        os.system("pip install google-generativeai")
        import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    response = model.generate_content([
        f"""From this text extracted from a Benin topographic survey, extract ONLY the coordinate table.
        
        Find the table with points (P1, P2, P3... or B1, B2, B3...) and their X, Y coordinates.
        X coordinates are typically between 390000-430000
        Y coordinates are typically between 650000-1300000
        
        Return ONLY a JSON format like this:
        {{
          "coordinates": [
            {{"point": "P1", "x": 401234.56, "y": 712345.78}},
            {{"point": "P2", "x": 401456.78, "y": 712567.89}}
          ]
        }}
        
        If no coordinates found, return: {{"coordinates": []}}
        
        Text to analyze:
        {text}"""
    ])
    
    return response.text

# === Pipeline principal (comme process_images dans hackatonia.py) ===
def process_images(api_key: str, input_folder: str = INPUT_FOLDER, output_folder: str = OUTPUT_FOLDER):
    """Pipeline principal d'extraction (équivalent process_images)"""
    results = []
    
    for file in Path(input_folder).glob("*"):
        if file.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            print(f"📄 Processing {file.name} ...")
            
            try:
                img = Image.open(file)
                
                # OCR avec Gemini (comme ocr_image_ollama)
                extracted_text = ocr_image_gemini(img, api_key)
                
                # Extraction coordonnées avec Gemini (comme check_ollama)
                coordinates_json = extract_coordinates_gemini(extracted_text, api_key)
                
                # Parser le JSON
                try:
                    # Nettoyer la réponse
                    clean_json = coordinates_json.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json.replace("```json", "").replace("```", "").strip()
                    elif clean_json.startswith("```"):
                        clean_json = clean_json.replace("```", "").strip()
                    
                    coord_data = json.loads(clean_json)
                    coordinates = coord_data.get("coordinates", [])
                    
                    # Valider les coordonnées
                    valid_coords = []
                    for coord in coordinates:
                        x = float(coord.get('x', 0))
                        y = float(coord.get('y', 0))
                        if 390000 <= x <= 430000 and 650000 <= y <= 1300000:
                            valid_coords.append(coord)
                    
                    results.append({
                        'image': file.name,
                        'coordinates': valid_coords,
                        'success': len(valid_coords) > 0
                    })
                    
                    print(f"✅ Done -> {len(valid_coords)} coordinates extracted")
                    
                except json.JSONDecodeError:
                    print(f"❌ JSON parsing failed for {file.name}")
                    results.append({
                        'image': file.name,
                        'coordinates': [],
                        'success': False
                    })
                
                # Sauvegarde du texte brut (comme dans hackatonia.py)
                output_file = Path(output_folder) / (file.stem + ".txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(extracted_text)
                    
            except Exception as e:
                print(f"❌ Error processing {file.name}: {e}")
                results.append({
                    'image': file.name,
                    'coordinates': [],
                    'success': False
                })
    
    return results

# === Génération du CSV final ===
def generate_submission_csv(results, output_file=OUTPUT_CSV):
    """Génère le fichier submission.csv"""
    headers = [
        'Nom_du_levé', 'Coordonnées', 'aif', 'air_proteges', 'dpl', 'dpm',
        'enregistrement individuel', 'litige', 'parcelles', 'restriction',
        'tf_demembres', 'tf_en_cours', 'tf_etat', 'titre_reconstitue', 'zone_inondable'
    ]
    
    rows = []
    for result in results:
        if result['success'] and result['coordinates']:
            coord_json = json.dumps([
                {"x": coord['x'], "y": coord['y']} 
                for coord in result['coordinates']
            ], separators=(',', ':'))
        else:
            coord_json = ""
        
        row = [result['image'], coord_json] + [''] * 13
        rows.append(row)
    
    df = pd.DataFrame(rows, columns=headers)
    df.to_csv(output_file, sep=';', index=False)
    print(f"📄 Fichier généré: {output_file}")

# === Lancer le pipeline (comme dans hackatonia.py) ===
if __name__ == "__main__":
    # Récupérer la clé API depuis .env
    if not GEMINI_API_KEY:
        print("❌ Clé API Gemini requise!")
        print("1. Obtenez une clé gratuite: https://makersuite.google.com/app/apikey")
        print("2. Ajoutez-la dans le fichier .env: GEMINI_API_KEY=votre_clé")
        exit(1)
    
    print(f"✅ Clé API Gemini chargée depuis .env")
    
    # Traiter les images
    results = process_images(GEMINI_API_KEY)
    
    # Générer le CSV
    generate_submission_csv(results)
    
    # Statistiques
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n✅ Traitement terminé!")
    print(f"📊 {successful}/{total} images traitées avec succès")
    print(f"📄 Fichier final: {OUTPUT_CSV}")

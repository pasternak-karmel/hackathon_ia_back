#!/usr/bin/env python3
"""
Extracteur Gemini pour les coordonnées des levés topographiques béninois
Hackathon Foncier Bénin 2025
"""

import json
import os
from pathlib import Path
from PIL import Image
import pandas as pd
from tqdm import tqdm
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiBeninExtractor:
    """Extracteur Gemini pour les levés topographiques béninois"""
    
    def __init__(self, api_key=None):
        """Initialise l'extracteur Gemini"""
        # Installer google-generativeai si nécessaire
        try:
            import google.generativeai as genai
            self.genai = genai
        except ImportError:
            logger.info("Installation de google-generativeai...")
            os.system("pip install google-generativeai")
            import google.generativeai as genai
            self.genai = genai
        
        # Configuration de l'API
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('GEMINI_API_KEY')
            if not self.api_key:
                logger.error("❌ Clé API Gemini requise!")
                logger.error("1. Obtenez une clé gratuite: https://makersuite.google.com/app/apikey")
                logger.error("2. Exportez-la: export GEMINI_API_KEY='votre_clé'")
                raise ValueError("Clé API Gemini manquante")
        
        # Configurer Gemini
        self.genai.configure(api_key=self.api_key)
        self.model = self.genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("✅ Gemini initialisé avec succès")
        
        # Paramètres spécifiques aux levés béninois
        self.benin_x_range = (390000, 430000)  # Coordonnées X plausibles
        self.benin_y_range = (650000, 1300000)  # Coordonnées Y plausibles
    
    def extract_coordinates_with_gemini(self, image_path):
        """Extrait les coordonnées avec Gemini Vision"""
        try:
            # Charger l'image
            img = Image.open(image_path)
            
            # Prompt spécialisé pour les levés topographiques béninois
            prompt = """Tu es un expert en levés topographiques. Analyse cette image de levé topographique béninois.

OBJECTIF: Extraire le tableau des coordonnées des bornes/points.

INSTRUCTIONS:
1. Trouve le tableau contenant les coordonnées des points (P1, P2, P3... ou B1, B2, B3...)
2. Chaque ligne contient: Numéro du point, Coordonnée X, Coordonnée Y
3. Les coordonnées X sont typiquement entre 390000-430000
4. Les coordonnées Y sont typiquement entre 650000-1300000
5. Ignore les autres informations (titre, surface, échelle, etc.)

FORMAT DE SORTIE REQUIS (JSON strict):
{
  "coordinates": [
    {"point": "P1", "x": 401234.56, "y": 712345.78},
    {"point": "P2", "x": 401456.78, "y": 712567.89}
  ]
}

RÈGLES IMPORTANTES:
- Retourne UNIQUEMENT le JSON, aucun autre texte
- Si aucune coordonnée trouvée: {"coordinates": []}
- Vérifie que les coordonnées sont dans les plages attendues
- Conserve la précision décimale si présente
- Nomme les points P1, P2, P3... dans l'ordre"""

            # Appel à Gemini
            response = self.model.generate_content([prompt, img])
            content = response.text.strip()
            
            # Nettoyer la réponse
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            
            # Parser le JSON
            try:
                result = json.loads(content)
                coordinates = result.get("coordinates", [])
                
                # Valider les coordonnées
                valid_coordinates = []
                for coord in coordinates:
                    if self.validate_coordinate(coord):
                        valid_coordinates.append(coord)
                
                return {
                    'success': True,
                    'coordinates': valid_coordinates,
                    'num_points': len(valid_coordinates)
                }
                
            except json.JSONDecodeError as e:
                logger.warning(f"Erreur JSON pour {image_path}: {e}")
                return {
                    'success': False,
                    'coordinates': [],
                    'num_points': 0
                }
                
        except Exception as e:
            logger.error(f"Erreur Gemini pour {image_path}: {e}")
            return {
                'success': False,
                'coordinates': [],
                'num_points': 0,
                'error': str(e)
            }
    
    def validate_coordinate(self, coord):
        """Valide une coordonnée"""
        try:
            x = float(coord.get('x', 0))
            y = float(coord.get('y', 0))
            
            return (self.benin_x_range[0] <= x <= self.benin_x_range[1] and
                    self.benin_y_range[0] <= y <= self.benin_y_range[1])
        except (ValueError, TypeError):
            return False
    
    def process_batch(self, input_dir, output_file="submission.csv"):
        """Traite un lot d'images avec Gemini"""
        input_path = Path(input_dir)
        
        # Trouver les images
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        image_files = [
            f for f in input_path.iterdir() 
            if f.suffix.lower() in image_extensions
        ]
        
        if not image_files:
            raise ValueError(f"Aucune image trouvée dans {input_dir}")
        
        logger.info(f"Traitement de {len(image_files)} images...")
        
        # Traiter chaque image
        results = []
        successful = 0
        
        for image_file in tqdm(image_files, desc="Extraction des coordonnées"):
            result = self.extract_coordinates_with_gemini(str(image_file))
            result['image_path'] = str(image_file)
            results.append(result)
            
            if result['success'] and result['num_points'] > 0:
                successful += 1
                logger.info(f"✅ {image_file.name}: {result['num_points']} points extraits")
            else:
                logger.warning(f"❌ {image_file.name}: échec d'extraction")
        
        # Générer le CSV
        self.generate_submission_csv(results, output_file)
        
        # Statistiques
        stats = {
            'total_images': len(image_files),
            'successful_extractions': successful,
            'success_rate': successful / len(image_files) * 100,
            'output_file': output_file
        }
        
        return stats
    
    def generate_submission_csv(self, results, output_file):
        """Génère le fichier submission.csv"""
        headers = [
            'Nom_du_levé', 'Coordonnées', 'aif', 'air_proteges', 'dpl', 'dpm',
            'enregistrement individuel', 'litige', 'parcelles', 'restriction',
            'tf_demembres', 'tf_en_cours', 'tf_etat', 'titre_reconstitue', 'zone_inondable'
        ]
        
        rows = []
        
        for result in results:
            image_name = Path(result['image_path']).name
            
            if result['success'] and result['coordinates']:
                # Formater les coordonnées en JSON
                coord_json = json.dumps([
                    {"x": coord['x'], "y": coord['y']} 
                    for coord in result['coordinates']
                ], separators=(',', ':'))
            else:
                coord_json = ""
            
            # Créer la ligne (coordonnées + 13 colonnes vides pour les intersections)
            row = [image_name, coord_json] + [''] * 13
            rows.append(row)
        
        # Sauvegarder le CSV
        df = pd.DataFrame(rows, columns=headers)
        df.to_csv(output_file, sep=';', index=False)
        
        logger.info(f"Fichier submission.csv généré: {output_file}")


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extraction des coordonnées des levés béninois')
    parser.add_argument('--input_dir', '-i', default='Testing Data', 
                       help='Dossier contenant les images de levés')
    parser.add_argument('--output', '-o', default='submission.csv',
                       help='Fichier de sortie CSV')
    parser.add_argument('--api_key', '-k', 
                       help='Clé API Gemini (ou utilisez GEMINI_API_KEY)')
    
    args = parser.parse_args()
    
    try:
        # Initialiser l'extracteur Gemini
        extractor = GeminiBeninExtractor(api_key=args.api_key)
        
        # Traiter les images
        stats = extractor.process_batch(args.input_dir, args.output)
        
        print(f"\n✅ Traitement terminé avec succès!")
        print(f"📊 Statistiques:")
        print(f"   - Images traitées: {stats['total_images']}")
        print(f"   - Extractions réussies: {stats['successful_extractions']}")
        print(f"   - Taux de réussite: {stats['success_rate']:.1f}%")
        print(f"📄 Fichier généré: {stats['output_file']}")
        
    except Exception as e:
        logger.error(f"Erreur fatale: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

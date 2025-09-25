#!/usr/bin/env python3
"""
Analyseur géospatial complet pour les levés topographiques béninois
Exemple qui regroupe tout : intersection avec les 14 couches + visualisation
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt
import json
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class BeninGeospatialAnalyzer:
    """Analyseur géospatial pour les levés béninois"""
    
    def __init__(self, couches_dir="couche/"):
        """
        Initialise l'analyseur
        
        Args:
            couches_dir: Dossier contenant les couches GeoJSON
        """
        self.couches_dir = Path(couches_dir)
        
        # Les 14 couches dans l'ordre du CSV de soumission
        self.couches_names = [
            'aif', 'air_proteges', 'dpl', 'dpm', 'enregistrement individuel',
            'litige', 'parcelles', 'restriction', 'tf_demembres', 'tf_en_cours',
            'tf_etat', 'titre_reconstitue', 'zone_inondable'
        ]
        
        print(f"🗺️ Analyseur géospatial initialisé")
        print(f"📁 Dossier couches: {self.couches_dir}")
        print(f"📊 {len(self.couches_names)} couches à analyser")
    
    def create_polygon_from_coordinates(self, coordinates):
        """
        Crée un polygone à partir des coordonnées
        
        Args:
            coordinates: Liste de dict [{"x": 433124.59, "y": 706444.25}, ...]
            
        Returns:
            Polygon Shapely
        """
        try:
            # Convertir en liste de tuples (x, y)
            points = [(coord["x"], coord["y"]) for coord in coordinates]
            
            # S'assurer que le polygone est fermé
            if points[0] != points[-1]:
                points.append(points[0])
            
            # Créer le polygone
            polygon = Polygon(points)
            
            # Vérifications
            if not polygon.is_valid:
                print("⚠️ Polygone invalide, tentative de correction...")
                polygon = polygon.buffer(0)  # Correction automatique
            
            print(f"✅ Polygone créé:")
            print(f"   - {len(coordinates)} points")
            print(f"   - Surface: {polygon.area:.2f} m²")
            print(f"   - Périmètre: {polygon.length:.2f} m")
            print(f"   - Valide: {polygon.is_valid}")
            
            return polygon
            
        except Exception as e:
            print(f"❌ Erreur création polygone: {e}")
            return None
    
    def analyze_single_layer(self, polygon, couche_name):
        """
        Analyse l'intersection avec une seule couche
        
        Args:
            polygon: Polygone Shapely du levé
            couche_name: Nom de la couche (ex: 'parcelles')
            
        Returns:
            Dict avec résultats détaillés
        """
        couche_path = self.couches_dir / f"{couche_name}.geojson"
        
        result = {
            'couche': couche_name,
            'has_intersection': False,
            'intersecting_features': 0,
            'total_features': 0,
            'intersection_area': 0.0,
            'percentage_covered': 0.0,
            'status': 'NON',
            'error': None
        }
        
        try:
            # Charger la couche
            if not couche_path.exists():
                result['error'] = f"Fichier {couche_path} non trouvé"
                return result
            
            gdf = gpd.read_file(couche_path)
            result['total_features'] = len(gdf)
            
            # Vérifier les intersections
            intersections = gdf.geometry.intersects(polygon)
            intersecting_features = gdf[intersections]
            
            if len(intersecting_features) > 0:
                result['has_intersection'] = True
                result['intersecting_features'] = len(intersecting_features)
                result['status'] = 'OUI'
                
                # Calculer la surface d'intersection totale
                total_intersection_area = 0
                for _, feature in intersecting_features.iterrows():
                    intersection = polygon.intersection(feature.geometry)
                    if hasattr(intersection, 'area'):
                        total_intersection_area += intersection.area
                
                result['intersection_area'] = total_intersection_area
                result['percentage_covered'] = (total_intersection_area / polygon.area) * 100
            
            print(f"   {couche_name:20} | {result['status']:3} | {result['intersecting_features']:3} features | {result['percentage_covered']:5.1f}%")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"   {couche_name:20} | ERR | Erreur: {e}")
        
        return result
    
    def analyze_all_intersections(self, coordinates):
        """
        Analyse complète avec toutes les couches
        
        Args:
            coordinates: Liste de dict [{"x": 433124.59, "y": 706444.25}, ...]
            
        Returns:
            Dict avec tous les résultats
        """
        print("\n🔍 === ANALYSE GÉOSPATIALE COMPLÈTE ===")
        
        # 1. Créer le polygone
        polygon = self.create_polygon_from_coordinates(coordinates)
        if polygon is None:
            return None
        
        # 2. Analyser chaque couche
        print(f"\n📊 Analyse des intersections:")
        print(f"{'Couche':20} | {'Int':3} | {'Features':8} | {'Couv.':5}")
        print("-" * 50)
        
        results = {
            'polygon_info': {
                'area': polygon.area,
                'perimeter': polygon.length,
                'centroid': {'x': polygon.centroid.x, 'y': polygon.centroid.y},
                'bounds': polygon.bounds
            },
            'intersections': {},
            'summary': {
                'total_intersections': 0,
                'intersecting_layers': []
            }
        }
        
        for couche_name in self.couches_names:
            layer_result = self.analyze_single_layer(polygon, couche_name)
            results['intersections'][couche_name] = layer_result
            
            if layer_result['has_intersection']:
                results['summary']['total_intersections'] += 1
                results['summary']['intersecting_layers'].append(couche_name)
        
        # 3. Résumé
        print(f"\n📋 === RÉSUMÉ ===")
        print(f"Surface du levé: {polygon.area:.2f} m² ({polygon.area/10000:.2f} ha)")
        print(f"Intersections trouvées: {results['summary']['total_intersections']}/13 couches")
        
        if results['summary']['intersecting_layers']:
            print(f"Couches intersectées:")
            for layer in results['summary']['intersecting_layers']:
                layer_result = results['intersections'][layer]
                print(f"  - {layer}: {layer_result['percentage_covered']:.1f}% du terrain")
        
        return results, polygon
    
    def generate_submission_row(self, coordinates, results):
        """
        Génère une ligne pour le fichier submission.csv
        
        Args:
            coordinates: Coordonnées originales
            results: Résultats de l'analyse
            
        Returns:
            Liste représentant une ligne CSV
        """
        # Coordonnées en JSON
        coord_json = json.dumps([{"x": coord["x"], "y": coord["y"]} for coord in coordinates])
        
        # Les 13 colonnes d'intersection dans l'ordre (sans 'enregistrement individuel' qui fait 14)
        intersection_values = []
        for couche_name in self.couches_names:
            if couche_name in results['intersections']:
                status = results['intersections'][couche_name]['status']
                intersection_values.append(status)
            else:
                intersection_values.append('')
        
        # Ligne complète: nom_fichier + coordonnées + 13 intersections
        row = ["exemple_leve.jpg", coord_json] + intersection_values
        
        return row
    
    def visualize_analysis(self, coordinates, results, polygon, save_path="analysis_visualization.png"):
        """
        Visualise l'analyse géospatiale
        
        Args:
            coordinates: Coordonnées originales
            results: Résultats de l'analyse
            polygon: Polygone Shapely
            save_path: Chemin de sauvegarde
        """
        print(f"\n🎨 Génération de la visualisation...")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Analyse Géospatiale du Levé Topographique', fontsize=16, fontweight='bold')
        
        # 1. Vue d'ensemble avec quelques couches importantes
        ax1 = axes[0, 0]
        
        # Charger et afficher quelques couches importantes
        important_layers = ['parcelles', 'zone_inondable', 'restriction']
        colors = ['lightblue', 'orange', 'red']
        
        for i, layer_name in enumerate(important_layers):
            layer_path = self.couches_dir / f"{layer_name}.geojson"
            if layer_path.exists():
                try:
                    gdf = gpd.read_file(layer_path)
                    # Filtrer autour du polygone pour la performance
                    bounds = polygon.bounds
                    buffer = 1000  # 1km de buffer
                    bbox = (bounds[0]-buffer, bounds[1]-buffer, bounds[2]+buffer, bounds[3]+buffer)
                    gdf_filtered = gdf.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
                    
                    if not gdf_filtered.empty:
                        gdf_filtered.plot(ax=ax1, color=colors[i], alpha=0.3, 
                                        edgecolor='black', linewidth=0.5, label=layer_name)
                except Exception as e:
                    print(f"Erreur visualisation {layer_name}: {e}")
        
        # Afficher le levé en rouge
        gdf_leve = gpd.GeoDataFrame([1], geometry=[polygon])
        gdf_leve.plot(ax=ax1, color='red', alpha=0.8, edgecolor='darkred', linewidth=2)
        
        ax1.set_title('Vue d\'ensemble du levé')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Graphique des intersections
        ax2 = axes[0, 1]
        
        intersection_data = []
        layer_names = []
        for couche_name in self.couches_names:
            if couche_name in results['intersections']:
                layer_result = results['intersections'][couche_name]
                intersection_data.append(1 if layer_result['has_intersection'] else 0)
                layer_names.append(couche_name.replace('_', '\n'))
        
        bars = ax2.bar(range(len(intersection_data)), intersection_data, 
                      color=['green' if x == 1 else 'lightgray' for x in intersection_data])
        ax2.set_title('Intersections par couche')
        ax2.set_ylabel('Intersection (1=Oui, 0=Non)')
        ax2.set_xticks(range(len(layer_names)))
        ax2.set_xticklabels(layer_names, rotation=45, ha='right', fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        # 3. Détails du polygone
        ax3 = axes[1, 0]
        
        # Coordonnées du polygone
        x_coords = [coord["x"] for coord in coordinates] + [coordinates[0]["x"]]
        y_coords = [coord["y"] for coord in coordinates] + [coordinates[0]["y"]]
        
        ax3.plot(x_coords, y_coords, 'ro-', linewidth=2, markersize=8)
        ax3.fill(x_coords, y_coords, alpha=0.3, color='red')
        
        # Annoter les points
        for i, coord in enumerate(coordinates):
            ax3.annotate(f'P{i+1}', (coord["x"], coord["y"]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=10)
        
        ax3.set_title('Détail du polygone du levé')
        ax3.set_xlabel('X (UTM 31N)')
        ax3.set_ylabel('Y (UTM 31N)')
        ax3.grid(True, alpha=0.3)
        ax3.axis('equal')
        
        # 4. Statistiques
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        stats_text = f"""
STATISTIQUES DU LEVÉ

Surface: {polygon.area:.2f} m²
        {polygon.area/10000:.4f} hectares

Périmètre: {polygon.length:.2f} m

Centroïde:
  X: {polygon.centroid.x:.2f}
  Y: {polygon.centroid.y:.2f}

INTERSECTIONS:
Total: {results['summary']['total_intersections']}/13 couches

Couches intersectées:
"""
        
        for layer in results['summary']['intersecting_layers']:
            layer_result = results['intersections'][layer]
            stats_text += f"• {layer}: {layer_result['percentage_covered']:.1f}%\n"
        
        ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Visualisation sauvegardée: {save_path}")
        plt.show()


def example_analysis():
    """Exemple d'utilisation complète"""
    
    # Coordonnées d'exemple (tes coordonnées)
    coordinates = [
    {"x": 392930.09, "y": 699294.99},
    {"x": 392922.77, "y": 699270.66},
    {"x": 392919.76, "y": 699249.80},
    {"x": 392871.22, "y": 699271.92},
    {"x": 392873.34, "y": 699293.50},
    {"x": 392874.36, "y": 699299.80},
    {"x": 392915.99, "y": 699294.09},
    {"x": 392925.48, "y": 699293.90}
]
    
    print("🚀 === EXEMPLE D'ANALYSE GÉOSPATIALE ===")
    print(f"📍 Coordonnées d'entrée: {len(coordinates)} points")
    for i, coord in enumerate(coordinates):
        print(f"   P{i+1}: X={coord['x']}, Y={coord['y']}")
    
    # Initialiser l'analyseur
    analyzer = BeninGeospatialAnalyzer()
    
    # Faire l'analyse complète
    results, polygon = analyzer.analyze_all_intersections(coordinates)
    
    if results:
        # Générer la ligne CSV
        csv_row = analyzer.generate_submission_row(coordinates, results)
        print(f"\n📄 Ligne CSV générée:")
        print(f"Longueur: {len(csv_row)} colonnes")
        print(f"Coordonnées: {csv_row[1][:50]}...")
        print(f"Intersections: {csv_row[2:]}")
        
        # Visualiser
        analyzer.visualize_analysis(coordinates, results, polygon)
        
        # Sauvegarder les résultats détaillés
        with open("analysis_results.json", "w", encoding="utf-8") as f:
            # Convertir le polygone en coordonnées pour JSON
            results_json = results.copy()
            results_json['polygon_coords'] = coordinates
            json.dump(results_json, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés: analysis_results.json")
        
        return results, csv_row
    
    else:
        print("❌ Échec de l'analyse")
        return None, None


if __name__ == "__main__":
    # Lancer l'exemple
    results, csv_row = example_analysis()

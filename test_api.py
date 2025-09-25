#!/usr/bin/env python3
"""
Script de test pour l'API d'extraction des coordonnées
"""

import requests
import json
import os
from pathlib import Path

API_BASE_URL = "http://127.0.0.1:8000"

def test_health_check():
    """Test du health check"""
    print("🏥 Test Health Check...")
    response = requests.get(f"{API_BASE_URL}/api/health/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_api_info():
    """Test des informations API"""
    print("\nℹ️ Test API Info...")
    response = requests.get(f"{API_BASE_URL}/api/info/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_extract_coordinates(file_path):
    """Test d'extraction des coordonnées"""
    print(f"\n🗺️ Test extraction coordonnées: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return False
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_BASE_URL}/api/extract-coordinates/", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Extraction réussie!")
            print(f"Coordonnées extraites: {len(data.get('coordinates', []))}")
            print(f"Taux de réussite: {data.get('validation', {}).get('success_rate', 0)}%")
            print(f"Fichier: {data.get('metadata', {}).get('filename', 'N/A')}")
            
            # Afficher quelques coordonnées
            coords = data.get('coordinates', [])[:3]
            for i, coord in enumerate(coords):
                print(f"  Point {i+1}: X={coord['x']}, Y={coord['y']}")
            
            if len(data.get('coordinates', [])) > 3:
                print(f"  ... et {len(data.get('coordinates', [])) - 3} autres points")
                
        else:
            print("❌ Erreur:")
            print(json.dumps(response.json(), indent=2))
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def find_test_files():
    """Trouve des fichiers de test"""
    test_dirs = [
        "Training Data",
        "Testing Data", 
        "."
    ]
    
    extensions = ['.png', '.jpg', '.jpeg', '.pdf']
    test_files = []
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for ext in extensions:
                files = list(Path(test_dir).glob(f"*{ext}"))
                test_files.extend(files)
    
    return test_files[:5]  # Limiter à 5 fichiers pour les tests

def main():
    """Fonction principale de test"""
    print("🚀 === TEST DE L'API BENIN SURVEY COORDINATES ===")
    
    # Test 1: Health Check
    health_ok = test_health_check()
    
    # Test 2: API Info
    info_ok = test_api_info()
    
    if not (health_ok and info_ok):
        print("❌ Tests de base échoués. Vérifiez que l'API est démarrée.")
        return
    
    # Test 3: Extraction de coordonnées
    print("\n🔍 Recherche de fichiers de test...")
    test_files = find_test_files()
    
    if not test_files:
        print("⚠️ Aucun fichier de test trouvé.")
        print("Placez des fichiers PNG, JPG ou PDF dans les dossiers:")
        print("- Training Data/")
        print("- Testing Data/")
        print("- Dossier courant")
        return
    
    print(f"📁 {len(test_files)} fichiers trouvés pour les tests")
    
    success_count = 0
    for file_path in test_files:
        if test_extract_coordinates(str(file_path)):
            success_count += 1
    
    # Résumé
    print(f"\n📊 === RÉSUMÉ DES TESTS ===")
    print(f"Health Check: {'✅' if health_ok else '❌'}")
    print(f"API Info: {'✅' if info_ok else '❌'}")
    print(f"Extraction: {success_count}/{len(test_files)} fichiers traités avec succès")
    
    if success_count == len(test_files):
        print("🎉 Tous les tests sont passés!")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les logs ci-dessus.")

if __name__ == "__main__":
    main()

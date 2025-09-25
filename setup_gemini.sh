#!/bin/bash
# Configuration rapide de Gemini pour l'extraction des levés béninois

echo "🚀 Configuration de Gemini pour l'extraction des coordonnées..."

# Installer google-generativeai
echo "📦 Installation de google-generativeai..."
pip install google-generativeai

echo ""
echo "🔑 Configuration de la clé API Gemini:"
echo ""
echo "1. Obtenez une clé API gratuite ici:"
echo "   👉 https://makersuite.google.com/app/apikey"
echo ""
echo "2. Exportez votre clé API:"
echo "   export GEMINI_API_KEY='votre_clé_api_ici'"
echo ""
echo "3. Ou utilisez directement:"
echo "   python3 gemini_extractor.py --api_key 'votre_clé_api_ici'"
echo ""
echo "✅ Installation terminée!"
echo ""
echo "Pour lancer l'extraction Gemini:"
echo "python3 gemini_extractor.py --input_dir 'Testing Data' --output submission_gemini.csv"

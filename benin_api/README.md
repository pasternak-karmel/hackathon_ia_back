# 🇧🇯 API Chatbot Expert Foncier Béninois

> **Hackathon Foncier Bénin 2025** - Intelligence Artificielle pour la gestion foncière

Une API Django REST complète avec chatbot IA spécialisé dans le foncier béninois, supportant les interactions multimodales (texte, audio, images).

## 🚀 Démo en ligne

**API déployée :** https://hackathon-ia-back-i10d.onrender.com

## ✨ Fonctionnalités

### 🤖 Chatbot Expert Foncier
- **Expert IA** spécialisé dans la législation foncière béninoise
- **Base de connaissances** : ANDF + Législation béninoise (547 documents)
- **Streaming en temps réel** des réponses
- **Sauvegarde automatique** des conversations

### 🎯 Multimodal
- **📝 Texte** : Questions classiques
- **🖼️ Images** : Analyse de titres fonciers, plans cadastraux
- **🎤 Audio** : Questions vocales multilingues
- **🎬 Vidéo** : Analyse de présentations foncières

### 📊 Gestion des Conversations
- **Historique complet** des conversations
- **API REST** pour récupérer les conversations
- **Base de données** SQLite/PostgreSQL
- **Métadonnées enrichies** pour chaque interaction

## 🛠️ Technologies

- **Backend :** Django 5.2.6 + Django REST Framework
- **IA :** Google Gemini 2.5 Flash (multimodal)
- **Base de connaissances :** FAISS + LangChain
- **Base de données :** SQLite (dev) / PostgreSQL (prod)
- **Déploiement :** Render
- **Documentation :** Swagger/OpenAPI

## 📋 Prérequis

- Python 3.10+
- Clé API Google Gemini
- Git

## 🔧 Installation

### 1. Cloner le repository
```bash
git clone https://github.com/pasternak-karmel/hackathon_ia_back.git
cd hackathon_ia_back
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances
```bash
cd benin_api
pip install -r requirements.txt
```

### 4. Configuration
Créer un fichier `.env` :
```env
GEMINI_API_KEY=votre_clé_api_gemini
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Migrations et démarrage
```bash
python manage.py migrate
python manage.py runserver
```

L'API sera accessible sur : http://127.0.0.1:8000

## 📚 Documentation API

### Endpoints principaux

#### 🤖 Chatbot (Endpoint unifié)
```http
POST /api/chatbot/ask/
```

**Mode Texte :**
```json
{
    "question": "Qu'est-ce qu'un titre foncier au Bénin ?"
}
```

**Mode Image :**
```json
{
    "question": "Analysez ce titre foncier",
    "image_file": "data:image/jpeg;base64,..."
}
```

**Mode Audio :**
```json
{
    "question": "Complétez avec cet audio",
    "audio_file": "data:audio/wav;base64,..."
}
```

**Réponse (streaming) :**
```json
data: {"type": "metadata", "question": "...", "conversation_id": "...", "media_type": "text", "has_media": false}
data: {"type": "chunk", "content": "En ", "accumulated": "En", "success": true}
data: {"type": "chunk", "content": "tant ", "accumulated": "En tant", "success": true}
data: {"type": "complete", "final_text": "...", "success": true}
data: {"type": "saved", "conversation_id": "...", "success": true}
```

#### 📋 Gestion des conversations
```http
GET /api/chatbot/conversations-list/          # Liste des conversations
GET /api/chatbot/conversation/{id}/messages/  # Détails d'une conversation
GET /api/chatbot/health/                      # Santé du service
```

### 📖 Documentation interactive
- **Swagger UI :** `/api/docs/`
- **ReDoc :** `/api/redoc/`
- **Schema OpenAPI :** `/api/schema/`

## 🎯 Exemples d'utilisation

### JavaScript (Fetch API)
```javascript
// Question texte
const response = await fetch('/api/chatbot/ask/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        question: "Comment obtenir un titre foncier au Bénin ?"
    })
});

// Lecture du streaming
const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = new TextDecoder().decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            console.log(data);
        }
    }
}
```

### Python (Requests)
```python
import requests

# Question avec image
response = requests.post('https://hackathon-ia-back-i10d.onrender.com/api/chatbot/ask/', 
    json={
        "question": "Analysez ce document foncier",
        "image_file": "data:image/jpeg;base64,..."
    },
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b'data: '):
        data = json.loads(line[6:])
        print(data)
```

### cURL
```bash
# Test de santé
curl https://hackathon-ia-back-i10d.onrender.com/api/chatbot/health/

# Question simple
curl -X POST https://hackathon-ia-back-i10d.onrender.com/api/chatbot/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Règlementations sur les titres fonciers au Bénin?"}'
```

## 🏗️ Architecture

```
benin_api/
├── benin_api/          # Configuration Django
│   ├── settings.py     # Paramètres
│   ├── urls.py         # Routes principales
│   └── requirements.txt
├── chatbot/            # App chatbot
│   ├── models.py       # Modèles (Conversation, Message)
│   ├── views.py        # Endpoints API
│   ├── urls.py         # Routes chatbot
│   ├── chatbot_service.py  # Service IA
│   ├── index.faiss     # Index FAISS
│   └── index.pkl       # Documents vectorisés
├── api/                # App extraction coordonnées
├── runtime.txt         # Version Python pour Render
└── manage.py
```

## 🔐 Sécurité

- **CORS** configuré pour les requêtes cross-origin
- **Variables d'environnement** pour les secrets
- **ALLOWED_HOSTS** configuré pour la production
- **DEBUG=False** en production

## 🚀 Déploiement

### Render (Recommandé)
1. Connecter le repository GitHub
2. Configurer les variables d'environnement :
   ```
   ALLOWED_HOSTS=votre-app.onrender.com
   DEBUG=False
   GEMINI_API_KEY=votre_clé
   ```
3. Build Command : `pip install -r benin_api/requirements.txt`
4. Start Command : `cd benin_api && python manage.py migrate && gunicorn benin_api.wsgi --bind 0.0.0.0:$PORT`

### Autres plateformes
- **Heroku :** Ajouter `Procfile`
- **Railway :** Configuration automatique
- **DigitalOcean App Platform :** Compatible

## 📊 Base de connaissances

- **547 documents** sur le foncier béninois
- **Sources :** ANDF + Législation officielle
- **Format :** Vectorisation FAISS + LangChain
- **Mise à jour :** Rechargement automatique

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit les changements (`git commit -m 'Ajout nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👥 Équipe

**Hackathon Foncier Bénin 2025**
- Développement IA et Backend
- Spécialisation foncier béninois
- Support multimodal

## 📞 Support

- **Issues :** [GitHub Issues](https://github.com/pasternak-karmel/hackathon_ia_back/issues)
- **Documentation :** [API Docs](https://hackathon-ia-back-i10d.onrender.com/api/docs/)
- **Email :** contact@hackathon-foncier-benin.com

## 🎯 Roadmap

- [ ] Support vidéo complet
- [ ] API de génération audio (TTS)
- [ ] Interface web React
- [ ] Authentification utilisateurs
- [ ] Analytics et métriques
- [ ] Support multilingue étendu (fon, yoruba)

---

**🇧🇯 Fait avec ❤️ pour le Hackathon Foncier Bénin 2025**

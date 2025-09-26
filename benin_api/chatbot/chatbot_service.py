"""Service de chatbot expert foncier béninois
Utilise FAISS + Gemini pour répondre aux questions sur le foncier
"""

import os
import pickle
import faiss
import numpy as np
from typing import List, Dict, Any
from google import genai
from django.conf import settings


class FoncierChatbotService:
    """
    Service de chatbot expert en foncier béninois
    """
    
    def __init__(self):
        self.client = None
        self.model_name = None
        self.index = None
        self.documents = None
        self._initialize()
    
    def _initialize(self):
        """Initialise le modèle et charge les index"""
        try:
            # Initialiser Gemini avec la nouvelle API
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY ou GEMINI_API_KEY non trouvée dans les variables d'environnement")
            
            # Configurer l'API key pour le client
            os.environ["GEMINI_API_KEY"] = api_key
            self.client = genai.Client()
            self.model_name = "gemini-2.5-flash"
            
            # Charger les index FAISS et documents
            self._load_knowledge_base()
            
        except Exception as e:
            print(f"Erreur initialisation chatbot: {e}")
            raise
    
    def _load_knowledge_base(self):
        """Charge la base de connaissances FAISS"""
        try:
            # Chemin vers les fichiers d'index
            base_path = os.path.dirname(__file__)
            faiss_path = os.path.join(base_path, "index.faiss")
            pkl_path = os.path.join(base_path, "index.pkl")
            
            # Essayer de charger les fichiers d'index
            try:
                if os.path.exists(pkl_path) and os.path.getsize(pkl_path) > 100:
                    with open(pkl_path, 'rb') as f:
                        self.documents = pickle.load(f)
                    print(f"✅ Documents chargés: {len(self.documents)} éléments")
                else:
                    raise FileNotFoundError("Fichier PKL invalide ou trop petit")
                    
                if os.path.exists(faiss_path) and os.path.getsize(faiss_path) > 100:
                    self.index = faiss.read_index(faiss_path)
                    print(f"✅ Index FAISS chargé: {self.index.ntotal} documents")
                else:
                    print("⚠️ Index FAISS invalide, utilisation sans recherche vectorielle")
                    self.index = None
                    
            except Exception as load_error:
                print(f"⚠️ Erreur chargement fichiers d'index: {load_error}")
                print("🔄 Utilisation de la base de connaissances par défaut")
                self.documents = self._get_default_knowledge()
                self.index = None
                
        except Exception as e:
            print(f"Erreur chargement base de connaissances: {e}")
            self.documents = self._get_default_knowledge()
            self.index = None
    
    def _get_default_knowledge(self):
        """Retourne des connaissances par défaut sur le foncier béninois"""
        return [
            "L'ANDF (Agence Nationale du Domaine et du Foncier) est l'institution chargée de la gestion foncière au Bénin, créée par la loi 2013-01.",
            "Un titre foncier est un document officiel qui atteste de la propriété d'une parcelle de terrain au Bénin.",
            "La plateforme eFoncier permet de réaliser des démarches foncières en ligne depuis janvier 2025 dans 12 communes.",
            "Plus de 74 532 titres fonciers ont été numérisés et intégrés à la base nationale béninoise.",
            "Le programme Terra Benin vise à cartographier 1,5 million de parcelles et enregistrer 1 million de titres fonciers.",
            "Les 14 couches géospatiales incluent les parcelles cadastrales, zones inondables, aires protégées, domaines publics, etc.",
            "Les litiges fonciers peuvent être résolus par médiation locale, conciliation administrative ou procédure judiciaire.",
            "Les services eFoncier incluent : demande de duplicata, mutation, état descriptif, radiation d'hypothèque.",
            "Les Bureaux communaux du domaine et du foncier sont les structures déconcentrées de l'ANDF.",
            "La formalisation foncière dans certaines communes doit être réalisée en ligne depuis le 1er janvier 2025."
        ]
    
    def search_relevant_documents(self, query: str, k: int = 5) -> List[str]:
        """
        Recherche les documents les plus pertinents pour une requête
        """
        try:
            if self.documents and len(self.documents) > 0:
                # Vérifier le type des documents
                if isinstance(self.documents, list) and isinstance(self.documents[0], str):
                    # Documents par défaut (chaînes de caractères)
                    return self.documents[:min(k, len(self.documents))]
                else:
                    # Documents chargés depuis FAISS (objets complexes)
                    # Extraire le texte des documents
                    text_docs = []
                    try:
                        # Si c'est un InMemoryDocstore ou un objet similaire
                        if hasattr(self.documents, 'docstore') and hasattr(self.documents.docstore, '_dict'):
                            # Extraire les documents du docstore
                            for doc_id, doc in list(self.documents.docstore._dict.items())[:k]:
                                if hasattr(doc, 'page_content'):
                                    text_docs.append(doc.page_content)
                                elif hasattr(doc, 'content'):
                                    text_docs.append(doc.content)
                                else:
                                    text_docs.append(str(doc))
                        elif hasattr(self.documents, '_dict'):
                            # Docstore direct
                            for doc_id, doc in list(self.documents._dict.items())[:k]:
                                if hasattr(doc, 'page_content'):
                                    text_docs.append(doc.page_content)
                                elif hasattr(doc, 'content'):
                                    text_docs.append(doc.content)
                                else:
                                    text_docs.append(str(doc))
                        else:
                            # Fallback: utiliser la base par défaut
                            return self._get_default_knowledge()[:k]
                    except Exception as extract_error:
                        print(f"Erreur extraction documents: {extract_error}")
                        return self._get_default_knowledge()[:k]
                    
                    return text_docs if text_docs else self._get_default_knowledge()[:k]
            
            # Fallback: base de connaissances par défaut
            return self._get_default_knowledge()[:k]
            
        except Exception as e:
            print(f"Erreur recherche documents: {e}")
            return self._get_default_knowledge()[:k]
    
    def generate_response(self, question: str, context_docs: List[str] = None) -> Dict[str, Any]:
        """
        Génère une réponse experte basée sur la question et le contexte
        """
        try:
            # Préparer le contexte
            context = ""
            if context_docs:
                context = " ".join(context_docs[:3])  # Limiter le contexte
            
            # Prompt système spécialisé foncier béninois
            system_prompt = """Tu es un expert juridique et technique en foncier béninois avec 20 ans d'expérience.

EXPERTISE :
- Code foncier et domanial du Bénin
- Procédures d'immatriculation et de morcellement  
- Gestion des litiges fonciers
- Analyse géospatiale des parcelles
- Réglementation ANDF (Agence Nationale du Domaine et du Foncier)
- Plateforme eFoncier et services numériques

STYLE DE RÉPONSE OBLIGATOIRE :
- Réponse en un seul paragraphe fluide et continu
- PAS de retours à la ligne (\n) dans la réponse
- PAS de formatage markdown (**, -, *, etc.)
- PAS de listes à puces ou numérotées
- PAS d'émojis dans la réponse
- Réponse claire, précise et professionnelle
- Intégrer naturellement les informations dans un texte continu
- Maximum 200 mots

DONNÉES DISPONIBLES :
- Informations officielles ANDF
- Législation foncière béninoise
- Procédures administratives
- Services eFoncier disponibles"""

            # Construire le message
            if context:
                user_message = f"""CONTEXTE (informations officielles ANDF) : {context}

QUESTION : {question}

Réponds en tant qu'expert foncier béninois en un seul paragraphe continu, sans retours à la ligne, sans émojis, sans formatage markdown. Intègre naturellement toutes les informations pertinentes dans un texte fluide."""
            else:
                user_message = f"""QUESTION : {question}

Réponds en tant qu'expert foncier béninois en un seul paragraphe continu, sans retours à la ligne, sans émojis, sans formatage markdown. Maximum 200 mots."""
            
            # Construire le prompt complet
            full_prompt = f"{system_prompt}\n\n{user_message}"
            
            # Générer la réponse avec la nouvelle API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            
            # Nettoyer la réponse
            cleaned_answer = self._clean_response(response.text)
            
            return {
                "success": True,
                "answer": cleaned_answer,
                "context_used": len(context_docs) if context_docs else 0,
                "source": "ANDF + Expert IA"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur génération réponse: {str(e)}",
                "answer": "Désolé, je ne peux pas répondre à cette question pour le moment."
            }
    
    def generate_response_stream(self, question: str, context_docs: List[str] = None):
        """
        Génère une réponse experte en streaming temps réel (comme ChatGPT)
        """
        try:
            # Préparer le contexte
            context = ""
            if context_docs:
                context = " ".join(context_docs[:3])  # Limiter le contexte
            
            # Prompt système spécialisé foncier béninois
            system_prompt = """Tu es un expert juridique et technique en foncier béninois avec 20 ans d'expérience.

EXPERTISE :
- Code foncier et domanial du Bénin
- Procédures d'immatriculation et de morcellement  
- Gestion des litiges fonciers
- Analyse géospatiale des parcelles
- Réglementation ANDF (Agence Nationale du Domaine et du Foncier)
- Plateforme eFoncier et services numériques

STYLE DE RÉPONSE OBLIGATOIRE :
- Réponse en un seul paragraphe fluide et continu
- PAS de retours à la ligne (\n) dans la réponse
- PAS de formatage markdown (**, -, *, etc.)
- PAS de listes à puces ou numérotées
- PAS d'émojis dans la réponse
- Réponse claire, précise et professionnelle
- Intégrer naturellement les informations dans un texte continu
- Maximum 200 mots

DONNÉES DISPONIBLES :
- Informations officielles ANDF
- Législation foncière béninoise
- Procédures administratives
- Services eFoncier disponibles"""

            # Construire le prompt complet
            if context:
                full_prompt = f"""{system_prompt}

CONTEXTE (informations officielles ANDF) : {context}

QUESTION : {question}

Réponds en tant qu'expert foncier béninois en un seul paragraphe continu, sans retours à la ligne, sans émojis, sans formatage markdown. Intègre naturellement toutes les informations pertinentes dans un texte fluide."""
            else:
                full_prompt = f"""{system_prompt}

QUESTION : {question}

Réponds en tant qu'expert foncier béninois en un seul paragraphe continu, sans retours à la ligne, sans émojis, sans formatage markdown. Maximum 200 mots."""
            
            # Générer la réponse (simuler le streaming)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            
            # Simuler le streaming en divisant la réponse
            full_text = self._clean_response(response.text)
            words = full_text.split()
            accumulated_text = ""
            
            # Simuler le streaming mot par mot
            for i, word in enumerate(words):
                accumulated_text += word + " "
                yield {
                    "type": "chunk",
                    "content": word + " ",
                    "accumulated": accumulated_text.strip(),
                    "success": True
                }
            
            # Envoyer le message de fin
            yield {
                "type": "complete",
                "final_text": accumulated_text,
                "context_used": len(context_docs) if context_docs else 0,
                "source": "ANDF + Expert IA",
                "success": True
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": f"Erreur génération streaming: {str(e)}",
                "success": False
            }
    
    def generate_response_stream_with_history(self, question: str, context_docs: List[str] = None, conversation_history: List[Dict] = None):
        """
        Génère une réponse experte en streaming avec historique de conversation (5 derniers messages)
        """
        try:
            # Préparer le contexte
            context = ""
            if context_docs:
                context = " ".join(context_docs[:3])  # Limiter le contexte
            
            # Préparer l'historique (garder les 5 derniers messages)
            history_context = ""
            if conversation_history:
                recent_history = conversation_history[-5:]  # 5 derniers messages
                history_parts = []
                for msg in recent_history:
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role and content:
                        if role == 'user':
                            history_parts.append(f"Utilisateur: {content}")
                        elif role == 'assistant':
                            history_parts.append(f"Expert: {content}")
                
                if history_parts:
                    history_context = " ".join(history_parts)
            
            # Prompt système spécialisé foncier béninois
            system_prompt = """Tu es un expert juridique et technique en foncier béninois avec 20 ans d'expérience.

EXPERTISE :
- Code foncier et domanial du Bénin
- Procédures d'immatriculation et de morcellement  
- Gestion des litiges fonciers
- Analyse géospatiale des parcelles
- Réglementation ANDF (Agence Nationale du Domaine et du Foncier)
- Plateforme eFoncier et services numériques

STYLE DE RÉPONSE OBLIGATOIRE :
- Réponse en un seul paragraphe fluide et continu
- PAS de retours à la ligne (\n) dans la réponse
- PAS de formatage markdown (**, -, *, etc.)
- PAS de listes à puces ou numérotées
- PAS d'émojis dans la réponse
- Réponse claire, précise et professionnelle
- Intégrer naturellement les informations dans un texte continu
- Tenir compte de l'historique de conversation pour donner une réponse cohérente
- Maximum 200 mots

DONNÉES DISPONIBLES :
- Informations officielles ANDF
- Législation foncière béninoise
- Procédures administratives
- Services eFoncier disponibles"""

            # Construire le prompt complet avec historique
            prompt_parts = [system_prompt]
            
            if context:
                prompt_parts.append(f"CONTEXTE (informations officielles ANDF) : {context}")
            
            if history_context:
                prompt_parts.append(f"HISTORIQUE DE CONVERSATION : {history_context}")
            
            prompt_parts.append(f"NOUVELLE QUESTION : {question}")
            prompt_parts.append("Réponds en tant qu'expert foncier béninois en un seul paragraphe continu, sans retours à la ligne, sans émojis, sans formatage markdown. Tiens compte de l'historique de conversation pour donner une réponse cohérente et contextuelle.")
            
            full_prompt = "\n\n".join(prompt_parts)
            
            # Générer la réponse (la nouvelle API ne supporte pas encore le streaming natif)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            
            # Simuler le streaming en divisant la réponse
            full_text = self._clean_response(response.text)
            words = full_text.split()
            accumulated_text = ""
            
            # Simuler le streaming mot par mot
            for i, word in enumerate(words):
                accumulated_text += word + " "
                yield {
                    "type": "chunk",
                    "content": word + " ",
                    "accumulated": accumulated_text.strip(),
                    "success": True
                }
            
            # Envoyer le message de fin
            yield {
                "type": "complete",
                "final_text": accumulated_text,
                "context_used": len(context_docs) if context_docs else 0,
                "history_used": len(conversation_history) if conversation_history else 0,
                "source": "ANDF + Expert IA",
                "success": True
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": f"Erreur génération streaming avec historique: {str(e)}",
                "success": False
            }
    
    def _clean_chunk(self, chunk: str) -> str:
        """
        Nettoie un chunk de streaming en temps réel
        """
        if not chunk:
            return ""
        
        # Supprimer les retours à la ligne
        cleaned = chunk.replace('\n', ' ').replace('\r', ' ')
        
        # Supprimer le formatage markdown basique
        cleaned = cleaned.replace('**', '').replace('*', '').replace('_', '')
        cleaned = cleaned.replace('###', '').replace('##', '').replace('#', '')
        
        # Supprimer les émojis simples (version légère pour le streaming)
        import re
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   "]+", flags=re.UNICODE)
        cleaned = emoji_pattern.sub('', cleaned)
        
        return cleaned
    
    def _clean_response(self, response: str) -> str:
        """
        Nettoie la réponse en supprimant les retours à la ligne et le formatage
        """
        if not response:
            return ""
        
        # S'assurer que la réponse est en UTF-8 propre
        if isinstance(response, bytes):
            response = response.decode('utf-8')
        
        # Supprimer tous les retours à la ligne
        cleaned = response.replace('\n', ' ').replace('\r', ' ')
        
        # Supprimer le formatage markdown
        cleaned = cleaned.replace('**', '').replace('*', '').replace('_', '')
        cleaned = cleaned.replace('###', '').replace('##', '').replace('#', '')
        cleaned = cleaned.replace('- ', '').replace('• ', '')
        
        # Supprimer les émojis (caractères Unicode d'émojis)
        import re
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)
        cleaned = emoji_pattern.sub('', cleaned)
        
        # Nettoyer les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Supprimer les espaces en début et fin
        cleaned = cleaned.strip()
        
        # S'assurer que les caractères spéciaux français sont corrects
        cleaned = cleaned.replace('Ã©', 'é').replace('Ã¨', 'è').replace('Ã ', 'à')
        cleaned = cleaned.replace('Ã´', 'ô').replace('Ã¹', 'ù').replace('Ã§', 'ç')
        
        return cleaned
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """
        Point d'entrée principal pour poser une question
        """
        try:
            # Rechercher des documents pertinents
            relevant_docs = self.search_relevant_documents(question)
            
            # Générer la réponse
            response = self.generate_response(question, relevant_docs)
            
            # Ajouter des métadonnées
            response["question"] = question
            response["timestamp"] = "now"  # Django ajoutera le timestamp
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur traitement question: {str(e)}",
                "question": question,
                "answer": "Une erreur s'est produite. Veuillez réessayer."
            }


# Instance globale du service
_chatbot_service = None

def get_chatbot_service() -> FoncierChatbotService:
    """
    Retourne l'instance singleton du service chatbot
    """
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = FoncierChatbotService()
    return _chatbot_service

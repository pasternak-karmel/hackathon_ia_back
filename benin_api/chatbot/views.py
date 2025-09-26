"""
Vues API pour le chatbot expert foncier béninois
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .chatbot_service import get_chatbot_service

logger = logging.getLogger(__name__)


@api_view(['POST'])
def ask_chatbot(request):
    """
    Endpoint principal pour poser une question au chatbot expert foncier avec streaming et historique
    
    POST /api/chatbot/ask/
    {
        "question": "Ma parcelle est-elle en règle ?",
        "context": {
            "coordinates": [404000, 719000],
            "parcelle_id": "optional"
        },
        "conversation_history": [
            {"role": "user", "content": "Qu'est-ce que l'ANDF ?"},
            {"role": "assistant", "content": "L'ANDF est l'Agence Nationale..."},
            {"role": "user", "content": "Quels sont ses services ?"}
        ]
    }
    """
    from django.http import StreamingHttpResponse
    import json
    
    try:
        # Récupérer les paramètres
        question = request.data.get('question', '').strip()
        context = request.data.get('context', {})
        conversation_history = request.data.get('conversation_history', [])
        
        if not question:
            return Response({
                "success": False,
                "error": "Question requise"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log de la question
        logger.info(f"Question chatbot: {question[:100]}...")
        
        def generate_stream():
            """Générateur pour le streaming temps réel de la réponse avec historique"""
            try:
                # Obtenir le service chatbot
                chatbot = get_chatbot_service()
                
                # Envoyer les métadonnées d'abord
                metadata = {
                    "type": "metadata",
                    "question": question,
                    "context": context,
                    "source": "ANDF + Expert IA",
                    "streaming": True,
                    "conversation_history_count": len(conversation_history)
                }
                yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
                
                # Rechercher des documents pertinents
                relevant_docs = chatbot.search_relevant_documents(question)
                
                # Streamer la réponse en temps réel avec Gemini et historique
                for chunk_data in chatbot.generate_response_stream_with_history(question, relevant_docs, conversation_history):
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "error": f"Erreur streaming: {str(e)}",
                    "success": False
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
        
        # Toujours retourner une réponse streamée
        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/event-stream; charset=utf-8'
        )
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        response['X-Accel-Buffering'] = 'no'  # Pour nginx
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur chatbot API: {e}")
        return Response({
            "success": False,
            "error": "Erreur interne du serveur",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def chatbot_health(request):
    """
    Vérification de santé du chatbot
    
    GET /api/chatbot/health/
    """
    try:
        chatbot = get_chatbot_service()
        
        # Test basique
        test_response = chatbot.ask_question("Test de fonctionnement")
        
        return Response({
            "status": "healthy",
            "service": "Chatbot Expert Foncier Béninois",
            "model": "Gemini 2.0 Flash",
            "knowledge_base": "ANDF + Législation béninoise",
            "documents_loaded": len(chatbot.documents) if chatbot.documents else 0,
            "test_successful": test_response.get("success", False)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "status": "unhealthy",
            "error": str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
def chatbot_conversation(request):
    """
    Endpoint pour une conversation continue avec historique
    
    POST /api/chatbot/conversation/
    {
        "messages": [
            {"role": "user", "content": "Qu'est-ce qu'un titre foncier ?"},
            {"role": "assistant", "content": "Un titre foncier est..."},
            {"role": "user", "content": "Comment l'obtenir ?"}
        ]
    }
    """
    try:
        messages = request.data.get('messages', [])
        
        if not messages or not isinstance(messages, list):
            return Response({
                "success": False,
                "error": "Liste de messages requise"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer la dernière question de l'utilisateur
        last_user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                last_user_message = msg.get('content', '').strip()
                break
        
        if not last_user_message:
            return Response({
                "success": False,
                "error": "Aucune question utilisateur trouvée"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Construire le contexte de conversation
        conversation_context = []
        for msg in messages[-5:]:  # Garder les 5 derniers messages
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role and content:
                conversation_context.append(f"{role}: {content}")
        
        # Obtenir le service chatbot
        chatbot = get_chatbot_service()
        
        # Enrichir la question avec le contexte de conversation
        enriched_question = f"""HISTORIQUE DE CONVERSATION:
{chr(10).join(conversation_context)}

NOUVELLE QUESTION: {last_user_message}"""
        
        # Traiter la question
        response_data = chatbot.ask_question(enriched_question)
        
        # Formater la réponse pour la conversation
        if response_data.get("success"):
            new_message = {
                "role": "assistant",
                "content": response_data["answer"],
                "timestamp": "now",
                "source": response_data.get("source", "Expert IA")
            }
            
            return Response({
                "success": True,
                "message": new_message,
                "conversation_id": request.data.get('conversation_id', 'default'),
                "context_used": response_data.get("context_used", 0)
            }, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Erreur conversation chatbot: {e}")
        return Response({
            "success": False,
            "error": "Erreur traitement conversation",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
def chatbot_info(request):
    """
    Informations sur le chatbot et ses capacités
    
    GET /api/chatbot/info/
    """
    return Response({
        "name": "Expert Foncier Béninois",
        "version": "1.0.0",
        "description": "Chatbot spécialisé en droit foncier et procédures administratives du Bénin",
        "capabilities": [
            "Questions sur la législation foncière béninoise",
            "Procédures d'immatriculation et de morcellement",
            "Gestion des litiges fonciers",
            "Services eFoncier et ANDF",
            "Analyse géospatiale des parcelles",
            "Recommandations juridiques"
        ],
        "languages": ["français"],
        "data_sources": [
            "Site officiel ANDF (andf.bj)",
            "Code foncier et domanial du Bénin",
            "Procédures administratives",
            "Jurisprudence foncière"
        ],
        "model": "Google Gemini 2.0 Flash",
        "last_updated": "2025-01-25",
        "features": [
            "Réponses nettoyées sans formatage",
            "Streaming des réponses",
            "Support des coordonnées géospatiales",
            "Conversations avec historique"
        ]
    }, status=status.HTTP_200_OK)

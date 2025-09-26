"""
Vues API pour le chatbot expert foncier béninois
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .chatbot_service import get_chatbot_service
from .models import Conversation, Message
from .serializers import (
    ConversationListSerializer, 
    ConversationDetailSerializer, 
    ConversationCreateSerializer,
    MessageSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
def ask_chatbot(request):
    """
    Endpoint principal pour poser une question au chatbot expert foncier avec streaming et historique
    MAINTENANT AVEC SAUVEGARDE AUTOMATIQUE EN BASE DE DONNÉES + SUPPORT MULTIMODAL
    
    POST /api/chatbot/ask/
    {
        "question": "Ma parcelle est-elle en règle ?",
        "context": {
            "coordinates": [404000, 719000],
            "parcelle_id": "optional"
        },
        "conversation_id": "uuid-optional",  // Si fourni, ajoute à la conversation existante
        "conversation_history": [...],
        "audio_file": "base64_encoded_audio",  // NOUVEAU: Support audio
        "image_file": "base64_encoded_image",  // NOUVEAU: Support image
        "media_type": "text|audio|image"      // NOUVEAU: Type de média
    }
    """
    from django.http import StreamingHttpResponse
    import json
    
    try:
        # Récupérer les paramètres (COMPATIBILITÉ MULTIMODALE AJOUTÉE)
        question = request.data.get('question', '').strip()
        context = request.data.get('context', {})
        conversation_history = request.data.get('conversation_history', [])
        conversation_id = request.data.get('conversation_id', None)
        
        # NOUVEAUX PARAMÈTRES MULTIMODAUX (optionnels pour rétrocompatibilité)
        media_type = request.data.get('media_type', 'text')
        media_data = request.data.get('media_data', '')
        audio_file = request.data.get('audio_file', '')  # Alternative pour audio
        image_file = request.data.get('image_file', '')  # Alternative pour image
        
        # DÉTECTION AUTOMATIQUE DU TYPE DE MÉDIA
        if not media_data and audio_file:
            media_data = audio_file
            media_type = 'audio'
        elif not media_data and image_file:
            media_data = image_file
            media_type = 'image'
        
        # Validation : question OU média requis
        if not question and not media_data:
            return Response({
                "success": False,
                "error": "Question ou fichier média requis"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log de la question
        logger.info(f"Question chatbot: {question[:100]}...")
        
        # Variables pour stocker la conversation
        conversation = None
        user_message = None
        ai_response_text = ""
        
        def generate_stream():
            """Générateur pour le streaming temps réel de la réponse avec historique ET sauvegarde"""
            nonlocal conversation, user_message, ai_response_text
            
            try:
                # 1. CRÉER OU RÉCUPÉRER LA CONVERSATION
                if conversation_id:
                    try:
                        conversation = Conversation.objects.get(id=conversation_id, is_active=True)
                    except Conversation.DoesNotExist:
                        conversation = None
                
                if not conversation:
                    # Créer une nouvelle conversation
                    conversation = Conversation.objects.create(
                        title=question[:50] + ('...' if len(question) > 50 else ''),
                        user=request.user if request.user.is_authenticated else None
                    )
                
                # 2. SAUVEGARDER LE MESSAGE UTILISATEUR (avec info multimodale)
                user_content = question if question else f"[Fichier {media_type} envoyé]"
                user_message = Message.objects.create(
                    conversation=conversation,
                    role='user',
                    content=user_content,
                    context_used={
                        "context": context,
                        "media_type": media_type,
                        "has_media": bool(media_data)
                    }
                )
                
                # Obtenir le service chatbot
                chatbot = get_chatbot_service()
                
                # Envoyer les métadonnées d'abord (avec info multimodale)
                metadata = {
                    "type": "metadata",
                    "question": question,
                    "context": context,
                    "source": "ANDF + Expert IA",
                    "streaming": True,
                    "conversation_history_count": len(conversation_history),
                    "conversation_id": str(conversation.id),
                    "saved_to_database": True,
                    "media_type": media_type,  # NOUVEAU: Type de média
                    "has_media": bool(media_data)  # NOUVEAU: Présence de média
                }
                yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
                
                # TRAITEMENT MULTIMODAL OU TEXTE
                if media_type != 'text' and media_data:
                    # TRAITEMENT MULTIMODAL (image/audio)
                    if media_type == 'image':
                        response_data = chatbot.process_image_with_question(question or "", media_data, context)
                    elif media_type == 'audio':
                        response_data = chatbot.process_audio_with_question(question or "", media_data, context)
                    else:
                        # Fallback vers traitement texte
                        relevant_docs = chatbot.search_relevant_documents(question)
                        response_data = chatbot.generate_response(question, relevant_docs)
                    
                    # Simuler le streaming pour le multimodal (pour garder le même format)
                    if response_data.get("success"):
                        full_text = response_data["answer"]
                        words = full_text.split()
                        accumulated_text = ""
                        
                        for word in words:
                            accumulated_text += word + " "
                            chunk_data = {
                                "type": "chunk",
                                "content": word + " ",
                                "accumulated": accumulated_text.strip(),
                                "success": True,
                                "media_processed": media_type  # NOUVEAU: Indique le type de média traité
                            }
                            ai_response_text += word + " "
                            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        
                        # Message final pour multimodal
                        final_chunk = {
                            "type": "complete",
                            "final_text": full_text,
                            "context_used": 0,
                            "source": "ANDF + Expert IA",
                            "success": True,
                            "media_type": media_type,
                            "processing_method": response_data.get("method", "multimodal")
                        }
                        yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                    else:
                        # Erreur multimodale
                        error_chunk = {
                            "type": "error",
                            "error": f"Erreur traitement {media_type}: {response_data.get('error', 'Erreur inconnue')}",
                            "success": False
                        }
                        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                        return
                else:
                    # TRAITEMENT TEXTE NORMAL (comportement existant)
                    relevant_docs = chatbot.search_relevant_documents(question)
                    
                    # Streamer la réponse en temps réel avec Gemini et historique
                    for chunk_data in chatbot.generate_response_stream_with_history(question, relevant_docs, conversation_history):
                        # Accumuler le texte de la réponse IA
                        if chunk_data.get("type") == "chunk":
                            ai_response_text += chunk_data.get("content", "")
                        
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                # 3. SAUVEGARDER LA RÉPONSE IA COMPLÈTE
                if ai_response_text.strip():
                    ai_message = Message.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=ai_response_text.strip(),
                        context_used={
                            "documents_used": len(relevant_docs) if 'relevant_docs' in locals() else 0,
                            "context": context,
                            "media_type": media_type,
                            "processing_method": "multimodal" if media_type != 'text' else "text"
                        }
                    )
                    
                    # Envoyer un message final avec les IDs sauvegardés
                    final_chunk = {
                        "type": "saved",
                        "conversation_id": str(conversation.id),
                        "user_message_id": str(user_message.id),
                        "ai_message_id": str(ai_message.id),
                        "success": True,
                        "message": "Conversation sauvegardée en base de données"
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                    
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


@api_view(['GET'])
def get_all_conversations(request):
    """
    Endpoint simple pour récupérer toutes les conversations sauvegardées
    
    GET /api/chatbot/conversations-list/
    """
    try:
        # Récupérer toutes les conversations actives
        conversations = Conversation.objects.filter(is_active=True).order_by('-updated_at')
        
        # Filtrer par utilisateur si authentifié
        if request.user.is_authenticated:
            conversations = conversations.filter(user=request.user)
        else:
            conversations = conversations.filter(user__isnull=True)
        
        # Construire la réponse
        conversations_data = []
        for conv in conversations:
            last_message = conv.messages.last()
            conversations_data.append({
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "messages_count": conv.messages.count(),
                "last_message": {
                    "role": last_message.role,
                    "content": last_message.content[:100] + ('...' if len(last_message.content) > 100 else ''),
                    "timestamp": last_message.timestamp.isoformat()
                } if last_message else None
            })
        
        return Response({
            "success": True,
            "count": len(conversations_data),
            "conversations": conversations_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erreur récupération conversations: {e}")
        return Response({
            "success": False,
            "error": "Erreur récupération conversations",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_conversation_messages(request, conversation_id):
    """
    Endpoint pour récupérer tous les messages d'une conversation
    
    GET /api/chatbot/conversation/{conversation_id}/messages/
    """
    try:
        # Récupérer la conversation
        conversation = Conversation.objects.get(id=conversation_id, is_active=True)
        
        # Vérifier les permissions
        if request.user.is_authenticated:
            if conversation.user != request.user:
                return Response({
                    "success": False,
                    "error": "Accès non autorisé à cette conversation"
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            if conversation.user is not None:
                return Response({
                    "success": False,
                    "error": "Accès non autorisé à cette conversation"
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Récupérer tous les messages
        messages = conversation.messages.all().order_by('timestamp')
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "context_used": msg.context_used
            })
        
        return Response({
            "success": True,
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages_count": len(messages_data)
            },
            "messages": messages_data
        }, status=status.HTTP_200_OK)
        
    except Conversation.DoesNotExist:
        return Response({
            "success": False,
            "error": "Conversation introuvable"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur récupération messages: {e}")
        return Response({
            "success": False,
            "error": "Erreur récupération messages",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationViewSet(ModelViewSet):
    """
    ViewSet pour gérer les conversations avec le chatbot
    """
    queryset = Conversation.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return ConversationCreateSerializer
        else:
            return ConversationDetailSerializer
    
    def get_queryset(self):
        """Filtrer par utilisateur si authentifié"""
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            return queryset.filter(user=self.request.user)
        return queryset.filter(user__isnull=True)  # Conversations anonymes
    
    def perform_create(self, serializer):
        """Créer une conversation avec l'utilisateur actuel"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Envoyer un message dans une conversation
        POST /api/conversations/{id}/send_message/
        {
            "content": "Ma question sur le foncier",
            "context": {"coordinates": [404000, 719000]}
        }
        """
        conversation = self.get_object()
        content = request.data.get('content', '').strip()
        context = request.data.get('context', {})
        
        if not content:
            return Response({
                "success": False,
                "error": "Contenu du message requis"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Sauvegarder le message utilisateur
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                content=content
            )
            
            # Obtenir l'historique de la conversation
            conversation_history = []
            for msg in conversation.messages.all()[-10:]:  # 10 derniers messages
                conversation_history.append({
                    'role': msg.role,
                    'content': msg.content
                })
            
            # Générer la réponse IA
            chatbot = get_chatbot_service()
            relevant_docs = chatbot.search_relevant_documents(content)
            response_data = chatbot.generate_response(content, relevant_docs)
            
            if response_data.get("success"):
                # Sauvegarder la réponse IA
                ai_message = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=response_data["answer"],
                    context_used={
                        "documents_used": len(relevant_docs) if relevant_docs else 0,
                        "context": context
                    }
                )
                
                # Mettre à jour le titre de la conversation si vide
                if not conversation.title:
                    conversation.title = content[:50] + ('...' if len(content) > 50 else '')
                    conversation.save()
                
                return Response({
                    "success": True,
                    "user_message": MessageSerializer(user_message).data,
                    "ai_message": MessageSerializer(ai_message).data,
                    "conversation": ConversationDetailSerializer(conversation).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": "Erreur génération réponse IA"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Erreur envoi message: {e}")
            return Response({
                "success": False,
                "error": "Erreur interne du serveur",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'])
    def delete_conversation(self, request, pk=None):
        """
        Supprimer une conversation (soft delete)
        DELETE /api/conversations/{id}/delete_conversation/
        """
        conversation = self.get_object()
        conversation.is_active = False
        conversation.save()
        
        return Response({
            "success": True,
            "message": "Conversation supprimée"
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Obtenir les conversations récentes
        GET /api/conversations/recent/
        """
        recent_conversations = self.get_queryset()[:10]  # 10 plus récentes
        serializer = ConversationListSerializer(recent_conversations, many=True)
        
        return Response({
            "success": True,
            "conversations": serializer.data,
            "count": len(serializer.data)
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
def ask_chatbot_multimodal(request):
    """
    Endpoint pour questions multimodales (audio, image, vidéo)
    
    POST /api/chatbot/multimodal/
    {
        "question": "Analysez ce document foncier",
        "media_type": "image|audio|video",
        "media_data": "base64_encoded_data",
        "context": {...},
        "conversation_id": "uuid-optional"
    }
    """
    try:
        # Récupérer les paramètres
        question = request.data.get('question', '').strip()
        media_type = request.data.get('media_type', 'text')
        media_data = request.data.get('media_data', '')
        context = request.data.get('context', {})
        conversation_id = request.data.get('conversation_id', None)
        
        if not question and not media_data:
            return Response({
                "success": False,
                "error": "Question ou média requis"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Variables pour stocker la conversation
        conversation = None
        user_message = None
        
        try:
            # 1. CRÉER OU RÉCUPÉRER LA CONVERSATION
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(id=conversation_id, is_active=True)
                except Conversation.DoesNotExist:
                    conversation = None
            
            if not conversation:
                # Créer une nouvelle conversation
                title = question[:50] if question else f"Analyse {media_type}"
                conversation = Conversation.objects.create(
                    title=title + ('...' if len(title) > 50 else ''),
                    user=request.user if request.user.is_authenticated else None
                )
            
            # 2. SAUVEGARDER LE MESSAGE UTILISATEUR
            user_content = question if question else f"[Fichier {media_type} envoyé]"
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                content=user_content,
                context_used={
                    "context": context,
                    "media_type": media_type,
                    "has_media": bool(media_data)
                }
            )
            
            # 3. TRAITER LE MÉDIA ET GÉNÉRER LA RÉPONSE
            chatbot = get_chatbot_service()
            
            if media_type == 'image' and media_data:
                # Traitement d'image
                response_data = chatbot.process_image_with_question(question, media_data, context)
            elif media_type == 'audio' and media_data:
                # Traitement audio
                response_data = chatbot.process_audio_with_question(question, media_data, context)
            else:
                # Fallback vers traitement texte normal
                relevant_docs = chatbot.search_relevant_documents(question)
                response_data = chatbot.generate_response(question, relevant_docs)
            
            if response_data.get("success"):
                # 4. SAUVEGARDER LA RÉPONSE IA
                ai_message = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=response_data["answer"],
                    context_used={
                        "media_processed": media_type,
                        "context": context,
                        "processing_method": response_data.get("method", "text")
                    }
                )
                
                return Response({
                    "success": True,
                    "conversation_id": str(conversation.id),
                    "user_message": MessageSerializer(user_message).data,
                    "ai_message": MessageSerializer(ai_message).data,
                    "media_type": media_type,
                    "processing_info": response_data.get("processing_info", {})
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": "Erreur traitement multimodal",
                    "details": response_data.get("error", "Erreur inconnue")
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Erreur traitement multimodal: {e}")
            return Response({
                "success": False,
                "error": "Erreur interne du serveur",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Erreur endpoint multimodal: {e}")
        return Response({
            "success": False,
            "error": "Erreur interne du serveur",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

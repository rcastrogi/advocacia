"""
API de Busca Global - Petitio
Permite buscar clientes, processos, petições e documentos em uma única pesquisa.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db, limiter
from app.rate_limits import AUTH_API_LIMIT
from app.models import Client, Process, SavedPetition, Document
import re

bp = Blueprint("search_api", __name__, url_prefix="/api/search")


def sanitize_search(query: str) -> str:
    """Sanitiza a query de busca"""
    if not query:
        return ""
    # Remove caracteres especiais perigosos, mantém espaços e acentos
    query = re.sub(r'[<>"\';%]', '', query.strip())
    return query[:100]  # Limita a 100 caracteres


@bp.route("/global", methods=["GET"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def global_search():
    """
    Busca global em clientes, processos, petições e documentos.
    
    Query params:
        q: termo de busca (mínimo 2 caracteres)
        limit: máximo de resultados por categoria (default: 5, max: 10)
    
    Returns:
        JSON com resultados agrupados por categoria
    """
    query = sanitize_search(request.args.get("q", ""))
    limit = min(int(request.args.get("limit", 5)), 10)
    
    if len(query) < 2:
        return jsonify({
            "success": True,
            "results": [],
            "total": 0,
            "query": query
        })
    
    results = []
    search_term = f"%{query}%"
    
    # Buscar Clientes
    try:
        clients = Client.query.filter(
            Client.lawyer_id == current_user.id,
            or_(
                Client.full_name.ilike(search_term),
                Client.email.ilike(search_term),
                Client.cpf_cnpj.ilike(search_term),
                Client.mobile_phone.ilike(search_term)
            )
        ).limit(limit).all()
        
        for client in clients:
            results.append({
                "type": "client",
                "type_label": "Cliente",
                "icon": "fa-user",
                "id": client.id,
                "title": client.full_name,
                "subtitle": client.email or client.mobile_phone or "",
                "url": f"/clients/{client.id}"
            })
    except Exception:
        pass  # Tabela pode não existir
    
    # Buscar Processos
    try:
        processes = Process.query.filter(
            Process.user_id == current_user.id,
            or_(
                Process.process_number.ilike(search_term),
                Process.title.ilike(search_term),
                Process.court.ilike(search_term),
                Process.plaintiff.ilike(search_term),
                Process.defendant.ilike(search_term)
            )
        ).limit(limit).all()
        
        for process in processes:
            results.append({
                "type": "process",
                "type_label": "Processo",
                "icon": "fa-gavel",
                "id": process.id,
                "title": process.process_number or process.title,
                "subtitle": process.title if process.process_number else (process.court or ""),
                "url": f"/processes/{process.id}"
            })
    except Exception:
        pass
    
    # Buscar Petições Salvas
    try:
        petitions = SavedPetition.query.filter(
            SavedPetition.user_id == current_user.id,
            or_(
                SavedPetition.title.ilike(search_term),
                SavedPetition.process_number.ilike(search_term),
                SavedPetition.notes.ilike(search_term)
            )
        ).limit(limit).all()
        
        for petition in petitions:
            # Obter tipo da petição se houver relação
            tipo_peticao = ""
            if petition.petition_type:
                tipo_peticao = petition.petition_type.name
            results.append({
                "type": "petition",
                "type_label": "Petição",
                "icon": "fa-file-alt",
                "id": petition.id,
                "title": petition.title or "Petição sem título",
                "subtitle": tipo_peticao or petition.process_number or "",
                "url": f"/petitions/saved/{petition.id}"
            })
    except Exception:
        pass
    
    # Buscar Documentos
    try:
        documents = Document.query.filter(
            Document.user_id == current_user.id,
            or_(
                Document.title.ilike(search_term),
                Document.description.ilike(search_term),
                Document.filename.ilike(search_term)
            )
        ).limit(limit).all()
        
        for doc in documents:
            results.append({
                "type": "document",
                "type_label": "Documento",
                "icon": "fa-file-pdf",
                "id": doc.id,
                "title": doc.title or doc.filename,
                "subtitle": doc.description[:50] if doc.description else "",
                "url": f"/documents/{doc.id}"
            })
    except Exception:
        pass
    
    # Ordenar por relevância (título exato primeiro)
    def relevance_score(item):
        title_lower = item["title"].lower()
        query_lower = query.lower()
        if title_lower == query_lower:
            return 0
        if title_lower.startswith(query_lower):
            return 1
        return 2
    
    results.sort(key=relevance_score)
    
    return jsonify({
        "success": True,
        "results": results,
        "total": len(results),
        "query": query
    })


@bp.route("/quick-actions", methods=["GET"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def quick_actions():
    """
    Retorna ações rápidas para o modal de busca.
    Exibidas quando o usuário abre o modal sem digitar nada.
    """
    actions = [
        {
            "type": "action",
            "icon": "fa-plus",
            "title": "Nova Petição",
            "subtitle": "Criar uma nova petição com IA",
            "url": "/peticoes/nova",
            "shortcut": "N"
        },
        {
            "type": "action",
            "icon": "fa-user-plus",
            "title": "Novo Cliente",
            "subtitle": "Cadastrar um novo cliente",
            "url": "/clientes/novo",
            "shortcut": "C"
        },
        {
            "type": "action",
            "icon": "fa-folder-plus",
            "title": "Novo Processo",
            "subtitle": "Cadastrar um novo processo",
            "url": "/processos/novo",
            "shortcut": "P"
        },
        {
            "type": "action",
            "icon": "fa-calendar-plus",
            "title": "Novo Prazo",
            "subtitle": "Adicionar prazo processual",
            "url": "/prazos/novo",
            "shortcut": "D"
        },
        {
            "type": "action",
            "icon": "fa-calculator",
            "title": "Calculadora Jurídica",
            "subtitle": "Correção monetária e juros",
            "url": "#",
            "action": "openCalculator",
            "shortcut": "J"
        },
        {
            "type": "action",
            "icon": "fa-chart-bar",
            "title": "Dashboard",
            "subtitle": "Visão geral do escritório",
            "url": "/dashboard",
            "shortcut": "H"
        }
    ]
    
    # Adicionar ações de admin se for master
    if current_user.is_master:
        actions.append({
            "type": "action",
            "icon": "fa-cogs",
            "title": "Administração",
            "subtitle": "Painel administrativo",
            "url": "/admin/",
            "shortcut": "A"
        })
    
    return jsonify({
        "success": True,
        "actions": actions
    })

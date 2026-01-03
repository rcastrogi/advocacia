#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API para votação em features do roadmap
"""

from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models import BillingPlan, RoadmapItem, UserPlan
from app.models_roadmap_votes import RoadmapVote, RoadmapVoteQuota

roadmap_votes_bp = Blueprint("roadmap_votes", __name__, url_prefix="/api/roadmap-votes")


def get_current_billing_period():
    """Retorna período de cobrança atual (YYYY-MM)"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def get_next_reset_date():
    """Retorna data do próximo reset de votos (próximo dia 1º do mês)"""
    now = datetime.now(timezone.utc)
    next_month = now + relativedelta(months=1)
    reset_date = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return reset_date


def ensure_vote_quota(user_id):
    """Cria ou atualiza quota de votos para o usuário no período atual"""
    period = get_current_billing_period()

    # Verificar se já existe quota para este período
    quota = RoadmapVoteQuota.query.filter_by(
        user_id=user_id, billing_period=period
    ).first()

    if quota:
        return quota

    # Obter plano atual do usuário
    user_plan = UserPlan.query.filter_by(
        user_id=user_id, is_current=True, status="active"
    ).first()

    if not user_plan:
        # Usuário sem plano ativo - 0 votos
        total_votes = 0
    else:
        # Pegar quantidade de votos do plano
        total_votes = user_plan.plan.votes_per_period or 0

    # Criar novo quota
    quota = RoadmapVoteQuota(
        user_id=user_id,
        billing_period=period,
        total_votes=total_votes,
        votes_used=0,
        reset_at=get_next_reset_date(),
    )
    db.session.add(quota)
    db.session.commit()

    return quota


@roadmap_votes_bp.route("/status", methods=["GET"])
@login_required
def get_vote_status():
    """Retorna status de votos do usuário"""
    quota = ensure_vote_quota(current_user.id)

    return jsonify(
        {
            "success": True,
            "quota": {
                "total_votes": quota.total_votes,
                "votes_used": quota.votes_used,
                "votes_remaining": quota.votes_remaining,
                "billing_period": quota.billing_period,
                "reset_at": quota.reset_at.isoformat(),
            },
            "period": get_current_billing_period(),
        }
    )


@roadmap_votes_bp.route("/vote", methods=["POST"])
@login_required
def cast_vote():
    """Registra voto do usuário em uma feature"""
    data = request.get_json()

    if not data or "roadmap_item_id" not in data:
        return jsonify(
            {"success": False, "error": "roadmap_item_id é obrigatório"}
        ), 400

    roadmap_item_id = data["roadmap_item_id"]
    votes_to_spend = data.get("votes", 1)  # Pode votar com múltiplos votos

    # Validar feature existe
    roadmap_item = RoadmapItem.query.get(roadmap_item_id)
    if not roadmap_item:
        return jsonify({"success": False, "error": "Feature não encontrada"}), 404

    # Obter quota
    quota = ensure_vote_quota(current_user.id)

    # Validar votos disponíveis
    if not quota.can_vote(votes_to_spend):
        return jsonify(
            {
                "success": False,
                "error": f"Votos insuficientes. Disponíveis: {quota.votes_remaining}",
            }
        ), 403

    # Verificar se já votou nesta feature neste período
    existing_vote = RoadmapVote.query.filter_by(
        user_id=current_user.id,
        roadmap_item_id=roadmap_item_id,
        billing_period=get_current_billing_period(),
    ).first()

    if existing_vote:
        # Usuário já votou - pode aumentar votos na mesma feature
        votes_additional = votes_to_spend
        existing_vote.votes_spent += votes_additional
        quota.votes_used += votes_additional
    else:
        # Primeiro voto nesta feature
        vote = RoadmapVote(
            user_id=current_user.id,
            roadmap_item_id=roadmap_item_id,
            votes_spent=votes_to_spend,
            billing_period=get_current_billing_period(),
        )
        db.session.add(vote)
        quota.votes_used += votes_to_spend

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f'{votes_to_spend} voto(s) registrado(s) em "{roadmap_item.title}"',
            "votes_remaining": quota.votes_remaining,
            "roadmap_item_id": roadmap_item_id,
        }
    )


@roadmap_votes_bp.route("/leaderboard", methods=["GET"])
def get_votes_leaderboard():
    """Retorna ranking das features mais votadas"""
    period = request.args.get("period", get_current_billing_period())
    limit = request.args.get("limit", 10, type=int)

    # Agregar votos por feature
    results = (
        db.session.query(
            RoadmapItem.id,
            RoadmapItem.title,
            RoadmapItem.status,
            db.func.sum(RoadmapVote.votes_spent).label("total_votes"),
            db.func.count(db.func.distinct(RoadmapVote.user_id)).label("unique_voters"),
        )
        .join(RoadmapVote, RoadmapItem.id == RoadmapVote.roadmap_item_id)
        .filter(RoadmapVote.billing_period == period)
        .group_by(RoadmapItem.id, RoadmapItem.title, RoadmapItem.status)
        .order_by(db.func.sum(RoadmapVote.votes_spent).desc())
        .limit(limit)
        .all()
    )

    leaderboard = [
        {
            "rank": i + 1,
            "roadmap_item_id": item[0],
            "title": item[1],
            "status": item[2],
            "total_votes": int(item[3]),
            "unique_voters": int(item[4]),
        }
        for i, item in enumerate(results)
    ]

    return jsonify({"success": True, "period": period, "leaderboard": leaderboard})


@roadmap_votes_bp.route("/my-votes", methods=["GET"])
@login_required
def get_my_votes():
    """Retorna votos do usuário atual"""
    period = request.args.get("period", get_current_billing_period())

    votes = (
        RoadmapVote.query.filter_by(user_id=current_user.id, billing_period=period)
        .join(RoadmapItem)
        .all()
    )

    user_votes = [
        {
            "roadmap_item_id": v.roadmap_item_id,
            "title": v.roadmap_item.title,
            "status": v.roadmap_item.status,
            "votes_spent": v.votes_spent,
            "voted_at": v.voted_at.isoformat(),
        }
        for v in votes
    ]

    return jsonify(
        {
            "success": True,
            "period": period,
            "votes": user_votes,
            "total_votes_spent": sum(v["votes_spent"] for v in user_votes),
        }
    )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modelos para sistema de votação em roadmap
"""

from app import db
from datetime import datetime, timezone
from decimal import Decimal

class RoadmapVote(db.Model):
    """Voto de usuário em feature do roadmap"""
    __tablename__ = "roadmap_votes"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    roadmap_item_id = db.Column(db.Integer, db.ForeignKey("roadmap_items.id"), nullable=False)
    votes_spent = db.Column(db.Integer, default=1)  # Quantos votos gastou nesta feature
    voted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    billing_period = db.Column(db.String(7), index=True)  # YYYY-MM do período que votou
    
    # Relacionamentos
    user = db.relationship("User", backref="roadmap_votes")
    roadmap_item = db.relationship("RoadmapItem", backref="votes")
    
    def __repr__(self):
        return f"<RoadmapVote user={self.user_id} item={self.roadmap_item_id} votes={self.votes_spent}>"


class RoadmapVoteQuota(db.Model):
    """Controle de votos disponíveis por usuário por período"""
    __tablename__ = "roadmap_vote_quotas"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    billing_period = db.Column(db.String(7), nullable=False, index=True)  # YYYY-MM
    total_votes = db.Column(db.Integer, nullable=False)  # Votos disponíveis
    votes_used = db.Column(db.Integer, default=0)  # Votos já gastos
    reset_at = db.Column(db.DateTime, nullable=False)  # Quando reseta
    
    # Relacionamento
    user = db.relationship("User", backref="vote_quotas")
    
    __table_args__ = (
        db.UniqueConstraint("user_id", "billing_period", name="uq_user_period_quota"),
    )
    
    @property
    def votes_remaining(self):
        """Votos restantes neste período"""
        return max(0, self.total_votes - self.votes_used)
    
    def can_vote(self, votes_to_spend=1):
        """Verifica se usuário pode votar"""
        return self.votes_remaining >= votes_to_spend
    
    def spend_votes(self, votes_to_spend=1):
        """Gasta votos do quota"""
        if self.can_vote(votes_to_spend):
            self.votes_used += votes_to_spend
            return True
        return False
    
    def __repr__(self):
        return f"<RoadmapVoteQuota user={self.user_id} period={self.billing_period} remaining={self.votes_remaining}>"

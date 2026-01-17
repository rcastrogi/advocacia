"""
API de Onboarding - Rastreia progresso de tours guiados
"""

from datetime import datetime, timezone

from flask import jsonify, request
from flask_login import current_user, login_required

from app import db, limiter
from app.rate_limits import AUTH_API_LIMIT

# Importar ou criar blueprint
try:
    from app.api import bp as api_bp
except ImportError:
    from flask import Blueprint

    api_bp = Blueprint("api", __name__)


class UserOnboarding(db.Model):
    """Rastreia progresso de onboarding e tours do usuário"""

    __tablename__ = "user_onboarding"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Status de tours completados
    lawyer_dashboard_completed = db.Column(db.Boolean, default=False)
    admin_dashboard_completed = db.Column(db.Boolean, default=False)
    processes_tour_completed = db.Column(db.Boolean, default=False)
    clients_tour_completed = db.Column(db.Boolean, default=False)
    petitions_tour_completed = db.Column(db.Boolean, default=False)
    billing_tour_completed = db.Column(db.Boolean, default=False)
    profile_tour_completed = db.Column(db.Boolean, default=False)
    roadmap_tour_completed = db.Column(db.Boolean, default=False)

    # Timestamps
    first_tour_at = db.Column(db.DateTime)
    last_tour_at = db.Column(db.DateTime)
    tour_completion_rate = db.Column(db.Integer, default=0)

    # Preferências
    skip_tours = db.Column(db.Boolean, default=False)
    show_tips = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento
    user = db.relationship("User", backref="onboarding", uselist=False)

    @classmethod
    def get_or_create(cls, user_id):
        """Obter ou criar registro de onboarding para um usuário"""
        onboarding = cls.query.filter_by(user_id=user_id).first()
        if not onboarding:
            onboarding = cls(user_id=user_id)
            db.session.add(onboarding)
            db.session.commit()
        return onboarding

    def mark_tour_completed(self, tour_name):
        """Marcar um tour como completado"""
        tour_field = f"{tour_name}_completed"
        if hasattr(self, tour_field):
            setattr(self, tour_field, True)
            self.last_tour_at = datetime.now(timezone.utc)
            if not self.first_tour_at:
                self.first_tour_at = self.last_tour_at
            self._update_completion_rate()
            db.session.commit()
            return True
        return False

    def _update_completion_rate(self):
        """Atualizar taxa de conclusão de tours"""
        tours = [
            self.lawyer_dashboard_completed,
            self.admin_dashboard_completed,
            self.processes_tour_completed,
            self.clients_tour_completed,
            self.petitions_tour_completed,
            self.billing_tour_completed,
            self.profile_tour_completed,
            self.roadmap_tour_completed,
        ]
        completed = sum(1 for t in tours if t)
        self.tour_completion_rate = int((completed / len(tours)) * 100)

    def to_dict(self):
        """Converter para dicionário"""
        return {
            "user_id": self.user_id,
            "tours_completed": {
                "lawyer_dashboard": self.lawyer_dashboard_completed,
                "admin_dashboard": self.admin_dashboard_completed,
                "processes": self.processes_tour_completed,
                "clients": self.clients_tour_completed,
                "petitions": self.petitions_tour_completed,
                "billing": self.billing_tour_completed,
                "profile": self.profile_tour_completed,
                "roadmap": self.roadmap_tour_completed,
            },
            "first_tour_at": self.first_tour_at.isoformat()
            if self.first_tour_at
            else None,
            "last_tour_at": self.last_tour_at.isoformat()
            if self.last_tour_at
            else None,
            "tour_completion_rate": self.tour_completion_rate,
            "skip_tours": self.skip_tours,
            "show_tips": self.show_tips,
        }


# Rotas da API


@api_bp.route("/onboarding/status", methods=["GET"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def get_onboarding_status():
    """Obter status de onboarding do usuário"""
    onboarding = UserOnboarding.get_or_create(current_user.id)

    return jsonify({"success": True, "data": onboarding.to_dict()})


@api_bp.route("/onboarding/tour/<tour_name>/complete", methods=["POST"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def mark_tour_complete(tour_name):
    """Marcar um tour como completado"""
    onboarding = UserOnboarding.get_or_create(current_user.id)

    if onboarding.mark_tour_completed(tour_name):
        return jsonify(
            {
                "success": True,
                "message": f'Tour "{tour_name}" marcado como completado',
                "completion_rate": onboarding.tour_completion_rate,
                "data": onboarding.to_dict(),
            }
        )

    return jsonify(
        {"success": False, "message": f'Tour "{tour_name}" não encontrado'}
    ), 400


@api_bp.route("/onboarding/preferences", methods=["POST"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def update_onboarding_preferences():
    """Atualizar preferências de onboarding"""
    data = request.get_json() or {}

    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    onboarding = UserOnboarding.get_or_create(current_user.id)

    # Atualizar preferências
    if "skip_tours" in data:
        onboarding.skip_tours = bool(data["skip_tours"])

    if "show_tips" in data:
        onboarding.show_tips = bool(data["show_tips"])

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Preferências atualizadas",
            "data": onboarding.to_dict(),
        }
    )


@api_bp.route("/onboarding/should-show-tour", methods=["GET"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def should_show_tour():
    """Verificar se deve mostrar tour para novo usuário"""
    onboarding = UserOnboarding.get_or_create(current_user.id)

    # Mostrar tour se: usuário não pulou tours E nunca viu um tour
    should_show = (
        not onboarding.skip_tours
        and not onboarding.first_tour_at
        and onboarding.tour_completion_rate == 0
    )

    return jsonify(
        {
            "success": True,
            "should_show_tour": should_show,
            "user_type": current_user.user_type,
            "is_new_user": (datetime.now(timezone.utc) - current_user.created_at).days
            < 1,
        }
    )

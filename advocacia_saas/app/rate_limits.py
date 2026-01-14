"""
Configuração de Rate Limiting com Flask-Limiter
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Inicializar limiter (será configurado na app)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
)

# ============================================================================
# DEFINIÇÕES DE RATE LIMITS POR TIPO DE ENDPOINT
# ============================================================================

# APIs públicas - limite mais restritivo
PUBLIC_API_LIMIT = "10 per minute"

# APIs autenticadas - limite moderado
AUTH_API_LIMIT = "30 per minute"

# APIs admin - limite maior
ADMIN_API_LIMIT = "60 per minute"

# Forms (envios de formulários) - muito restritivo
FORM_SUBMIT_LIMIT = "5 per minute"

# Login - muito restritivo (prevent brute force)
LOGIN_LIMIT = "5 per minute"

# Endpoints críticos - muito muito restritivo
CRITICAL_LIMIT = "2 per minute"

# Cupons - restritivo para evitar brute force de códigos
COUPON_LIMIT = "10 per minute"

# ============================================================================
# FUNÇÃO AUXILIAR PARA APLICAR LIMITES
# ============================================================================


def apply_rate_limits(app):
    """
    Aplicar rate limits aos blueprints e endpoints

    Uso na app.py:
        from app.rate_limits import apply_rate_limits
        apply_rate_limits(app)
    """

    # Login - muito restritivo
    limiter.limit(LOGIN_LIMIT)(
        app.blueprints.get("auth").view_functions.get("login")
    ) if "auth" in app.blueprints else None

    print("✅ Rate limiting aplicado com sucesso")


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================

"""
EXEMPLO 1: Aplicar limite a um blueprint inteiro

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.rate_limits import AUTH_API_LIMIT

limiter = Limiter(key_func=get_remote_address)

@api_bp.route('/users', methods=['GET'])
@limiter.limit(AUTH_API_LIMIT)
def list_users():
    return jsonify(users)


EXEMPLO 2: Aplicar limite a uma função específica

@limiter.limit("10 per minute")
def critical_operation():
    ...


EXEMPLO 3: Aplicar no blueprint inteiro

limiter.limit(AUTH_API_LIMIT)(api_bp)

"""

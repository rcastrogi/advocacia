# 🐍 Best Practices - Python/Flask

## 1. VALIDAÇÃO DE ENTRADA (Input Validation)

### Problema Atual
```python
# ❌ Ruim - Sem validação
@bp.route('/api/user/preferences', methods=['POST'])
@login_required
def api_save_user_preferences():
    data = request.get_json() or {}
    view_key = data.get('view_key')
    preferences = data.get('preferences')
    if not view_key or preferences is None:
        return jsonify({'error': '...'}), 400
    # ... resto
```

### Solução Recomendada
```python
from marshmallow import Schema, fields, validate, ValidationError

class UserPreferencesSchema(Schema):
    view_key = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=200),
        error_messages={'required': 'view_key é obrigatório'}
    )
    preferences = fields.Dict(
        required=True,
        validate=validate.Length(max=10000),
        error_messages={'required': 'preferences é obrigatório'}
    )

schema = UserPreferencesSchema()

@bp.route('/api/user/preferences', methods=['POST'])
@login_required
def api_save_user_preferences():
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': err.messages}), 400
    
    view_key = data['view_key']
    preferences = data['preferences']
    TablePreference.set_for_user(current_user.id, view_key, preferences)
    return jsonify({'success': True})
```

### Instalação
```bash
pip install marshmallow marshmallow-sqlalchemy
```

---

## 2. RATE LIMITING

### Problema Atual
Sem proteção contra brute force / DoS

### Solução
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Aplicar globalmente na app
limiter.init_app(app)

# Ou em rotas específicas
@bp.route('/api/user/preferences', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def api_save_user_preferences():
    # ...
```

### Com Redis (melhor)
```python
limiter = Limiter(
    app=app,
    key_func=lambda: current_user.id if current_user.is_authenticated else get_remote_address(),
    storage_uri=os.environ.get('REDIS_URL', 'memory://')
)
```

### Instalação
```bash
pip install flask-limiter
```

---

## 3. OTIMIZAÇÃO DE QUERIES (N+1 Problem)

### Problema Atual
```python
# ❌ Ruim - N+1 queries
plans = BillingPlan.query.all()
for plan in plans:
    user_count = User.query.filter_by(plan_id=plan.id).count()
    print(f"{plan.name}: {user_count} users")
# Query 1 + N queries adicionais = N+1
```

### Solução com Eager Loading
```python
from sqlalchemy.orm import joinedload

# ✅ Bom - Eager load
plans = BillingPlan.query.outerjoin(User).all()

# Ou com count
from sqlalchemy import func, select
plans = db.session.execute(
    select(BillingPlan, func.count(User.id).label('user_count'))
    .outerjoin(User)
    .group_by(BillingPlan.id)
).all()
```

### Em Models (Relationship)
```python
class BillingPlan(db.Model):
    users = db.relationship('User', lazy='select')
    
    # Lazy loading strategies:
    # - 'select': Carrega quando acessado (padrão)
    # - 'joined': Eager load com JOIN
    # - 'subquery': Eager load com subquery
    # - 'dynamic': Retorna query

# Uso
plans = BillingPlan.query.options(joinedload(BillingPlan.users)).all()
```

### Query Optimization Tips
```python
# ✅ Use select() do SQLAlchemy 2.0
from sqlalchemy import select

query = select(BillingPlan).where(BillingPlan.active == True)
plans = db.session.execute(query).scalars().all()

# ❌ Evitar .all() ao final se só precisa de COUNT
total = db.session.query(BillingPlan).count()  # Melhor: db.session.query(func.count(BillingPlan.id))

# ✅ Use .exists() para verificar existência
exists = db.session.query(BillingPlan.query.filter_by(name='Premium').exists()).scalar()
```

---

## 4. PAGINAÇÃO

### Problema Atual
Mix de DataTables (client-side) + Flask-Paginate (server-side)

### Solução - Padronizar em Server-Side
```python
from flask_sqlalchemy import Pagination

@bp.route('/api/plans')
def api_get_plans():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    paginated = BillingPlan.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        'items': [p.to_dict() for p in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page
    })
```

---

## 5. CACHING

### Redis Cache Pattern
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
    'CACHE_KEY_PREFIX': 'petitio:',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Uso
@bp.route('/api/plans')
@cache.cached(timeout=300, key_prefix='plans_list')
def get_plans():
    return jsonify([p.to_dict() for p in BillingPlan.query.all()])

# Invalidar cache
@bp.route('/api/plans', methods=['POST'])
def create_plan():
    plan = BillingPlan(...)
    db.session.add(plan)
    db.session.commit()
    cache.delete('plans_list')  # Limpar cache
    return jsonify(plan.to_dict()), 201
```

### Instalação
```bash
pip install flask-caching redis
```

---

## 6. ERROR HANDLING

### Bom Padrão
```python
from functools import wraps
from flask import jsonify

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400
        except PermissionError as e:
            return jsonify({'error': 'Unauthorized'}), 403
        except ValueError as e:
            return jsonify({'error': str(e)}), 422
        except Exception as e:
            app.logger.error(f"Unhandled error: {e}", exc_info=True)
            return jsonify({'error': 'Internal Server Error'}), 500
    return decorated_function

@bp.route('/api/plans', methods=['POST'])
@login_required
@handle_errors
def create_plan():
    # ...
```

---

## 7. LOGGING

### Padrão Recomendado
```python
import logging
from logging.handlers import RotatingFileHandler

# Config em __init__.py
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

# Uso em routes
@bp.route('/api/plans', methods=['POST'])
def create_plan():
    try:
        # ...
        app.logger.info(f"Plan created: {plan.id}")
        return jsonify(plan.to_dict()), 201
    except Exception as e:
        app.logger.error(f"Failed to create plan: {e}", exc_info=True)
        return jsonify({'error': 'Internal Server Error'}), 500
```

---

## 8. TESTING

### Test Structure
```
tests/
├── __init__.py
├── conftest.py          # Fixtures compartilhadas
├── test_models.py
├── test_routes.py
├── test_billing_api.py
└── test_admin_routes.py
```

### Exemplo com Pytest
```python
# tests/conftest.py
import pytest
from app import create_app, db
from app.models import User, BillingPlan

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_user(app):
    user = User(email='admin@test.com', is_admin=True)
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

# tests/test_billing_api.py
def test_create_plan(client, admin_user):
    client.login(admin_user.email, 'password123')
    response = client.post('/api/plans', json={
        'name': 'Premium',
        'monthly_fee': 99.00,
        'plan_type': 'monthly'
    })
    assert response.status_code == 201
    assert response.json['name'] == 'Premium'

def test_invalid_plan_creation(client, admin_user):
    client.login(admin_user.email, 'password123')
    response = client.post('/api/plans', json={
        'name': 'Premium',
        'monthly_fee': -99.00  # Invalid
    })
    assert response.status_code == 400
```

### Instalação
```bash
pip install pytest pytest-flask pytest-cov
```

### Rodar testes
```bash
pytest
pytest --cov=app tests/
pytest -v
```

---

## 9. TYPE HINTS

### Melhorar Código com Type Hints
```python
# ❌ Antes
def get_user_plans(user_id):
    user = User.query.get(user_id)
    if not user:
        return None
    return user.plans

# ✅ Depois
from typing import List, Optional

def get_user_plans(user_id: int) -> Optional[List[BillingPlan]]:
    user: Optional[User] = User.query.get(user_id)
    if not user:
        return None
    return user.plans

# Em Routes
@bp.route('/api/plans/<int:plan_id>')
def get_plan(plan_id: int) -> tuple[dict, int]:
    plan = BillingPlan.query.get_or_404(plan_id)
    return jsonify(plan.to_dict()), 200
```

### Instalação
```bash
pip install types-flask types-requests
mypy app/  # Type checking
```

---

## 10. DEPENDÊNCIAS RECOMENDADAS

### Adicionar ao requirements.txt
```
# Validação
marshmallow==3.20.1
marshmallow-sqlalchemy==0.29.0

# Rate Limiting
flask-limiter==3.5.0

# Cache
flask-caching==2.0.2
redis==5.0.1

# Testing
pytest==7.4.3
pytest-flask==1.3.0
pytest-cov==4.1.0

# Type Hints
types-flask==1.1.6
types-requests==2.31.0
mypy==1.7.1

# Logging
python-json-logger==2.0.7

# Security
python-dotenv==1.0.0
```

---

## CHECKLIST - PRÓXIMOS PASSOS

- [ ] Adicionar Marshmallow para validação
- [ ] Implementar Rate Limiting
- [ ] Otimizar N+1 queries
- [ ] Adicionar Type Hints
- [ ] Escrever testes unitários
- [ ] Configurar logging adequado
- [ ] Implementar caching com Redis
- [ ] Adicionar pré-commit hooks (mypy, black, flake8)

---

## FERRAMENTAS PARA QUALIDADE DE CÓDIGO

```bash
# Code formatting
pip install black
black app/

# Linting
pip install flake8 pylint
flake8 app/

# Type checking
pip install mypy
mypy app/

# Import sorting
pip install isort
isort app/

# Pre-commit (executar antes de commit)
pip install pre-commit
```

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
```

---


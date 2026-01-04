"""
Rotas para visualizar logs em produção
Acesso: /admin/logs (apenas admin)
"""

from flask import Blueprint, render_template_string, jsonify, request
from flask_login import login_required
from functools import wraps
import os
import logging

bp = Blueprint('logs', __name__, url_prefix='/admin')

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator para require admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.user_type != 'master':
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/logs')
@login_required
@admin_required
def view_logs():
    """Página para visualizar logs em tempo real"""
    
    log_file = 'logs/petitio_production.log'
    
    # Ler últimas N linhas
    lines = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                lines = all_lines[-200:]  # Últimas 200 linhas
        except Exception as e:
            lines = [f"❌ Erro ao ler logs: {str(e)}"]
    else:
        lines = ["📁 Arquivo de logs ainda não foi criado"]
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>📊 Logs do Render</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #1e1e1e; color: #d4d4d4; font-family: 'Courier New', monospace; }
            .log-container { background: #252526; border: 1px solid #3e3e42; border-radius: 5px; padding: 15px; }
            .log-line { margin: 2px 0; line-height: 1.4; }
            .error { color: #f48771; }
            .warning { color: #dcdcaa; }
            .info { color: #6a9955; }
            .debug { color: #9cdcfe; }
            .critical { color: #ff6b6b; background: #3d1f1f; padding: 2px 5px; }
            .btn-refresh { position: fixed; bottom: 20px; right: 20px; }
            header { background: #2d2d30; border-bottom: 2px solid #007bff; padding: 15px; }
            h1 { color: #007bff; }
        </style>
    </head>
    <body>
        <header>
            <div class="container-fluid">
                <h1>📊 Logs de Produção - Render</h1>
                <p class="text-muted">Últimas 200 linhas (atualizar página para ver novos logs)</p>
            </div>
        </header>
        
        <div class="container-fluid mt-4">
            <div class="log-container">
    '''
    
    # Adicionar linhas de log com colorização
    for line in lines:
        line = line.rstrip()
        
        # Colorizar por tipo
        if 'ERROR' in line or 'CRITICAL' in line or 'EXCEPTION' in line:
            if 'CRITICAL' in line or 'EXCEPTION' in line:
                css_class = 'critical'
            else:
                css_class = 'error'
        elif 'WARNING' in line:
            css_class = 'warning'
        elif 'INFO' in line:
            css_class = 'info'
        elif 'DEBUG' in line:
            css_class = 'debug'
        else:
            css_class = ''
        
        # Escapar HTML
        line = (line
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
        
        html += f'<div class="log-line {css_class}">{line}</div>\n'
    
    html += '''
            </div>
        </div>
        
        <button class="btn btn-primary btn-refresh" onclick="location.reload()">
            🔄 Atualizar
        </button>
        
        <div style="height: 100px;"></div>
        
        <script>
            // Auto-scroll para o final
            window.scrollTo(0, document.body.scrollHeight);
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html)

@bp.route('/logs/json')
@login_required
@admin_required
def get_logs_json():
    """API para obter logs em JSON"""
    
    log_file = 'logs/petitio_production.log'
    lines = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                lines = [line.rstrip() for line in all_lines[-100:]]  # Últimas 100
        except Exception as e:
            lines = [f"Erro ao ler logs: {str(e)}"]
    
    return jsonify({
        'success': True,
        'lines': lines,
        'count': len(lines),
        'file': log_file,
        'exists': os.path.exists(log_file)
    })

@bp.route('/logs/tail')
@login_required
@admin_required
def tail_logs():
    """Endpoint para tail -f (últimas linhas)"""
    
    log_file = 'logs/petitio_production.log'
    
    if not os.path.exists(log_file):
        return jsonify({'error': 'Log file not found'}), 404
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-50:]  # Últimas 50 linhas
        
        return jsonify({
            'success': True,
            'lines': last_lines,
            'count': len(last_lines)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

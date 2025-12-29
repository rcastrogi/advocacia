#!/usr/bin/env python3
"""
Script para testar acesso ao painel admin
"""

import os
import sys
import requests
from datetime import datetime

def test_admin_access():
    """Testa acesso ao painel admin via HTTP"""

    print("=== TESTE DE ACESSO AO PAINEL ADMIN ===")
    print(f"Data/Hora: {datetime.now()}")
    print()

    # URLs para testar (ajuste conforme necessário)
    base_url = "http://localhost:5000"  # Altere se necessário

    print("URLs de teste:")
    print(f"Login: {base_url}/auth/login")
    print(f"Admin Dashboard: {base_url}/admin/dashboard")
    print(f"Gerenciar Usuários: {base_url}/admin/usuarios")
    print()

    print("=== INSTRUÇÕES PARA TESTE MANUAL ===")
    print("1. Abra o navegador e vá para a página de login:")
    print(f"   {base_url}/auth/login")
    print()
    print("2. Faça login com as credenciais do admin:")
    print("   Email: admin@petitio.com")
    print("   Senha: admin123")
    print()
    print("3. Após login, você deve ver no menu superior direito:")
    print("   - Seu nome com badge 'Admin' (vermelho)")
    print("   - Opção 'Gerenciar Usuários' no dropdown")
    print()
    print("4. Clique em 'Gerenciar Usuários' ou acesse diretamente:")
    print(f"   {base_url}/admin/usuarios")
    print()
    print("=== POSSÍVEIS PROBLEMAS ===")
    print("❌ Se não conseguir fazer login:")
    print("   - Verifique se o servidor está rodando")
    print("   - Verifique as credenciais")
    print("   - Verifique se o usuário está ativo")
    print()
    print("❌ Se conseguir login mas não ver 'Gerenciar Usuários':")
    print("   - Você não está logado como usuário 'master'")
    print("   - Execute novamente: python fix_admin_access.py")
    print()
    print("❌ Se ver erro 403 (Forbidden):")
    print("   - Mesmo problema de permissões")
    print("   - Verifique o tipo do usuário no banco")
    print()
    print("=== LOGS PARA DEBUG ===")
    print("Verifique os logs em tempo real:")
    print("python monitor_portal_logs.py")
    print()
    print("Ou veja os logs recentes:")
    print("python monitor_portal_logs.py --recent 20")

if __name__ == "__main__":
    test_admin_access()
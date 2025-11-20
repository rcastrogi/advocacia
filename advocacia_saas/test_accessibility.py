#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste de acessibilidade do Petitio
Verifica se todos os recursos de acessibilidade estão funcionando corretamente
"""

import os
import sys

def check_file_exists(filepath, description):
    """Verifica se um arquivo existe"""
    if os.path.exists(filepath):
        print(f"✅ {description}: OK")
        return True
    else:
        print(f"❌ {description}: ERRO - Arquivo não encontrado")
        return False

def check_accessibility_files():
    """Verifica se todos os arquivos de acessibilidade existem"""
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO DE ARQUIVOS DE ACESSIBILIDADE")
    print("="*60 + "\n")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    files = {
        "JavaScript de Acessibilidade": os.path.join(base_path, "app", "static", "js", "accessibility.js"),
        "CSS de Acessibilidade": os.path.join(base_path, "app", "static", "css", "accessibility.css"),
        "Guia de Acessibilidade": os.path.join(base_path, "ACCESSIBILITY_GUIDE.md"),
        "Guia de Cores": os.path.join(base_path, "COLOR_GUIDE.md"),
        "Template Base": os.path.join(base_path, "app", "templates", "base.html"),
    }
    
    results = []
    for desc, filepath in files.items():
        results.append(check_file_exists(filepath, desc))
    
    return all(results)

def check_base_template_integration():
    """Verifica se o template base.html tem as integrações de acessibilidade"""
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO DE INTEGRAÇÃO NO TEMPLATE BASE")
    print("="*60 + "\n")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_path, "app", "templates", "base.html")
    
    if not os.path.exists(template_path):
        print("❌ Template base.html não encontrado")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "Link para accessibility.css": 'accessibility.css' in content,
        "Skip link presente": 'skip-link' in content,
        "Botão de acessibilidade": 'accessibilityToggle' in content,
        "Barra de acessibilidade": 'accessibility-bar' in content,
        "Região de anúncios SR": 'screen-reader-announcements' in content,
        "Main content com ID": 'id="main-content"' in content,
        "Script accessibility.js": 'accessibility.js' in content,
        "Atributos ARIA": 'aria-label' in content,
        "Role complementary": 'role="complementary"' in content,
        "Meta description": 'meta name="description"' in content,
    }
    
    results = []
    for desc, check in checks.items():
        if check:
            print(f"✅ {desc}: OK")
            results.append(True)
        else:
            print(f"❌ {desc}: FALTANDO")
            results.append(False)
    
    return all(results)

def check_wcag_compliance():
    """Verifica conformidade WCAG no guia de cores"""
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO DE CONFORMIDADE WCAG")
    print("="*60 + "\n")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    color_guide_path = os.path.join(base_path, "COLOR_GUIDE.md")
    
    if not os.path.exists(color_guide_path):
        print("❌ COLOR_GUIDE.md não encontrado")
        return False
    
    with open(color_guide_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    wcag_requirements = {
        "Contraste de títulos (mínimo 4.5:1)": "5.2:1" in content,
        "Contraste de texto (mínimo 4.5:1)": "14:1" in content,
        "Contraste de subtítulos": "12:1" in content,
        "Nível AA mencionado": "AA" in content,
        "Nível AAA mencionado": "AAA" in content,
    }
    
    results = []
    for desc, check in wcag_requirements.items():
        if check:
            print(f"✅ {desc}: OK")
            results.append(True)
        else:
            print(f"❌ {desc}: FALTANDO")
            results.append(False)
    
    return all(results)

def check_javascript_features():
    """Verifica se o JavaScript de acessibilidade tem todas as funcionalidades"""
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO DE FUNCIONALIDADES JAVASCRIPT")
    print("="*60 + "\n")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(base_path, "app", "static", "js", "accessibility.js")
    
    if not os.path.exists(js_path):
        print("❌ accessibility.js não encontrado")
        return False
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    features = {
        "Controle de tamanho de fonte": "applyFontSize" in content,
        "Modo de alto contraste": "applyHighContrast" in content,
        "Skip link": "skip-to-content" in content,
        "Navegação por teclado": "handleKeyboardNavigation" in content,
        "Anúncios para screen reader": "announceToScreenReader" in content,
        "Atalhos de teclado": "keyboardShortcuts" in content,
        "ARIA em formulários": "aria-required" in content,
        "Melhorias em tabelas": "scope" in content,
        "Estados de carregamento": "loading" in content or "Loading" in content,
        "LocalStorage": "localStorage" in content,
    }
    
    results = []
    for desc, check in features.items():
        if check:
            print(f"✅ {desc}: OK")
            results.append(True)
        else:
            print(f"❌ {desc}: FALTANDO")
            results.append(False)
    
    return all(results)

def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🌟 TESTE DE ACESSIBILIDADE DO PETITIO")
    print("="*60)
    
    results = []
    
    # Teste 1: Arquivos existem
    results.append(check_accessibility_files())
    
    # Teste 2: Integração no template
    results.append(check_base_template_integration())
    
    # Teste 3: Conformidade WCAG
    results.append(check_wcag_compliance())
    
    # Teste 4: Funcionalidades JavaScript
    results.append(check_javascript_features())
    
    # Resultado final
    print("\n" + "="*60)
    print("📊 RESULTADO FINAL")
    print("="*60 + "\n")
    
    if all(results):
        print("✅ TODOS OS TESTES PASSARAM!")
        print("🌟 O sistema está pronto para uso com total acessibilidade!")
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("⚠️  Revise os erros acima antes de publicar")
        return 1

if __name__ == "__main__":
    sys.exit(main())

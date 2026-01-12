"""
Script de verificação geral do código.
Analisa Python, HTML, JavaScript em busca de problemas comuns.

Uso: python scripts/code_checker.py
"""

import re
import sys
import ast
from pathlib import Path
from collections import defaultdict


# Cores para output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def colorize(text, color):
    """Adiciona cor ao texto"""
    return f"{color}{text}{Colors.RESET}"


# Diretórios
BASE_DIR = Path(__file__).parent.parent
APP_DIR = BASE_DIR / "app"
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


class CodeChecker:
    """Verificador de código"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = defaultdict(int)

    def add_error(self, file, line, message):
        self.errors.append({"file": file, "line": line, "message": message})
        self.stats["errors"] += 1

    def add_warning(self, file, line, message):
        self.warnings.append({"file": file, "line": line, "message": message})
        self.stats["warnings"] += 1

    def add_info(self, file, message):
        self.info.append({"file": file, "message": message})
        self.stats["info"] += 1

    def check_python_files(self):
        """Verifica arquivos Python"""
        print(colorize("\n📦 Verificando arquivos Python...", Colors.BLUE))

        for py_file in APP_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            self.stats["python_files"] += 1
            rel_path = py_file.relative_to(BASE_DIR)

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Verificar sintaxe Python
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    self.add_error(str(rel_path), e.lineno, f"Erro de sintaxe: {e.msg}")
                    continue

                # Verificar imports não usados (básico)
                self._check_unused_imports(str(rel_path), content)

                # Verificar linhas muito longas
                for i, line in enumerate(lines, 1):
                    if len(line) > 120:
                        self.add_warning(
                            str(rel_path), i, f"Linha muito longa ({len(line)} chars)"
                        )

                # Verificar print statements em código de produção
                for i, line in enumerate(lines, 1):
                    if re.match(r"^\s*print\s*\(", line):
                        # Ignorar em scripts/
                        if "scripts/" not in str(rel_path):
                            self.add_warning(
                                str(rel_path), i, "print() encontrado (usar logging)"
                            )

                # Verificar TODO/FIXME
                for i, line in enumerate(lines, 1):
                    if "TODO" in line or "FIXME" in line:
                        self.add_info(str(rel_path), f"Linha {i}: {line.strip()[:60]}")

                # Verificar == True/False (usar is)
                for i, line in enumerate(lines, 1):
                    if "== True" in line or "== False" in line:
                        self.add_warning(
                            str(rel_path), i, "Usar 'is True/False' em vez de '== True/False'"
                        )

                # Verificar except genérico
                for i, line in enumerate(lines, 1):
                    if re.match(r"^\s*except\s*:", line):
                        self.add_warning(
                            str(rel_path), i, "except genérico (especificar exceção)"
                        )

            except Exception as e:
                self.add_error(str(rel_path), 0, f"Erro ao ler arquivo: {e}")

    def _check_unused_imports(self, file_path, content):
        """Verifica imports potencialmente não usados"""
        try:
            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split(".")[0]
                        imports.append((name, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name != "*":
                            name = alias.asname or alias.name
                            imports.append((name, node.lineno))

            # Verificar uso (simplificado)
            for name, line in imports:
                # Contar ocorrências (excluindo a linha de import)
                pattern = rf"\b{re.escape(name)}\b"
                matches = re.findall(pattern, content)
                if len(matches) <= 1:
                    self.add_warning(
                        file_path, line, f"Import '{name}' possivelmente não usado"
                    )

        except Exception:
            pass

    def check_html_templates(self):
        """Verifica templates HTML"""
        print(colorize("\n🌐 Verificando templates HTML...", Colors.BLUE))

        for html_file in TEMPLATES_DIR.rglob("*.html"):
            self.stats["html_files"] += 1
            rel_path = html_file.relative_to(BASE_DIR)

            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Verificar blocos Jinja2
                ifs = len(re.findall(r"{%\s*if\s", content))
                endifs = len(re.findall(r"{%\s*endif\s*%}", content))
                if ifs != endifs:
                    self.add_error(
                        str(rel_path), 0, f"if/endif desbalanceados: {ifs} if, {endifs} endif"
                    )

                fors = len(re.findall(r"{%\s*for\s", content))
                endfors = len(re.findall(r"{%\s*endfor\s*%}", content))
                if fors != endfors:
                    self.add_error(
                        str(rel_path), 0, f"for/endfor desbalanceados: {fors} for, {endfors} endfor"
                    )

                # Verificar tags HTML não fechadas (básico)
                for tag in ["div", "span", "table", "form"]:
                    opens = len(re.findall(rf"<{tag}[\s>]", content, re.I))
                    closes = len(re.findall(rf"</{tag}>", content, re.I))
                    if opens > closes + 10:
                        self.add_warning(
                            str(rel_path), 0, f"Tag <{tag}> possivelmente não fechada ({opens} abertas, {closes} fechadas)"
                        )

                # Verificar imagens sem alt
                imgs_no_alt = re.findall(r"<img(?![^>]*\balt=)[^>]*>", content, re.I)
                if imgs_no_alt:
                    self.add_warning(
                        str(rel_path), 0, f"{len(imgs_no_alt)} imagens sem atributo alt"
                    )

                # Verificar links com target="_blank" sem rel="noopener"
                unsafe_links = re.findall(
                    r'<a[^>]*target=["\']_blank["\'](?![^>]*rel=)[^>]*>',
                    content,
                    re.I
                )
                if unsafe_links:
                    self.add_warning(
                        str(rel_path), 0, f"{len(unsafe_links)} links com target='_blank' sem rel='noopener'"
                    )

            except Exception as e:
                self.add_error(str(rel_path), 0, f"Erro ao ler arquivo: {e}")

    def check_javascript_files(self):
        """Verifica arquivos JavaScript"""
        print(colorize("\n📜 Verificando arquivos JavaScript...", Colors.BLUE))

        js_dir = STATIC_DIR / "js"
        if not js_dir.exists():
            return

        for js_file in js_dir.rglob("*.js"):
            self.stats["js_files"] += 1
            rel_path = js_file.relative_to(BASE_DIR)

            try:
                with open(js_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Verificar parênteses/chaves balanceados
                if content.count("(") != content.count(")"):
                    self.add_error(str(rel_path), 0, "Parênteses desbalanceados")

                if content.count("{") != content.count("}"):
                    self.add_error(str(rel_path), 0, "Chaves desbalanceadas")

                if content.count("[") != content.count("]"):
                    self.add_error(str(rel_path), 0, "Colchetes desbalanceados")

                # Verificar console.log
                console_logs = len(re.findall(r"console\.(log|debug)\(", content))
                if console_logs > 0:
                    self.add_warning(
                        str(rel_path), 0, f"{console_logs} console.log/debug encontrados"
                    )

                # Verificar eval (perigoso)
                if re.search(r"\beval\s*\(", content):
                    self.add_error(str(rel_path), 0, "Uso de eval() detectado (perigoso!)")

                # Verificar document.write
                if "document.write" in content:
                    self.add_warning(str(rel_path), 0, "document.write detectado (evitar)")

                # Verificar var vs let/const
                var_count = len(re.findall(r"\bvar\s+", content))
                if var_count > 10:
                    self.add_warning(
                        str(rel_path), 0, f"{var_count} usos de 'var' (considerar let/const)"
                    )

            except Exception as e:
                self.add_error(str(rel_path), 0, f"Erro ao ler arquivo: {e}")

    def check_css_files(self):
        """Verifica arquivos CSS"""
        print(colorize("\n🎨 Verificando arquivos CSS...", Colors.BLUE))

        css_dir = STATIC_DIR / "css"
        if not css_dir.exists():
            return

        for css_file in css_dir.rglob("*.css"):
            self.stats["css_files"] += 1
            rel_path = css_file.relative_to(BASE_DIR)

            try:
                with open(css_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Verificar chaves balanceadas
                if content.count("{") != content.count("}"):
                    self.add_error(str(rel_path), 0, "Chaves desbalanceadas")

                # Verificar !important excessivo
                importants = len(re.findall(r"!important", content))
                if importants > 30:
                    self.add_warning(
                        str(rel_path), 0, f"{importants} usos de !important (considerar refatoração)"
                    )

            except Exception as e:
                self.add_error(str(rel_path), 0, f"Erro ao ler arquivo: {e}")

    def print_report(self):
        """Imprime relatório final"""
        print(colorize("\n" + "=" * 60, Colors.BOLD))
        print(colorize("📊 RELATÓRIO DE VERIFICAÇÃO", Colors.BOLD))
        print(colorize("=" * 60, Colors.BOLD))

        # Estatísticas
        print("\n📁 Arquivos analisados:")
        print(f"   - Python: {self.stats['python_files']}")
        print(f"   - HTML: {self.stats['html_files']}")
        print(f"   - JavaScript: {self.stats['js_files']}")
        print(f"   - CSS: {self.stats['css_files']}")

        # Erros
        if self.errors:
            print(colorize(f"\n❌ ERROS ({len(self.errors)}):", Colors.RED))
            for err in self.errors[:20]:  # Limitar a 20
                print(f"   {err['file']}:{err['line']} - {err['message']}")
            if len(self.errors) > 20:
                print(f"   ... e mais {len(self.errors) - 20} erros")

        # Warnings
        if self.warnings:
            print(colorize(f"\n⚠️  AVISOS ({len(self.warnings)}):", Colors.YELLOW))
            for warn in self.warnings[:30]:  # Limitar a 30
                print(f"   {warn['file']}:{warn['line']} - {warn['message']}")
            if len(self.warnings) > 30:
                print(f"   ... e mais {len(self.warnings) - 30} avisos")

        # TODOs/FIXMEs
        if self.info:
            print(colorize(f"\n📝 TODOs/FIXMEs ({len(self.info)}):", Colors.BLUE))
            for info in self.info[:10]:
                print(f"   {info['file']}: {info['message']}")
            if len(self.info) > 10:
                print(f"   ... e mais {len(self.info) - 10} itens")

        # Resumo
        print(colorize("\n" + "=" * 60, Colors.BOLD))
        if self.errors:
            print(colorize(f"❌ {len(self.errors)} erros encontrados", Colors.RED))
        else:
            print(colorize("✅ Nenhum erro encontrado!", Colors.GREEN))

        print(colorize(f"⚠️  {len(self.warnings)} avisos", Colors.YELLOW))
        print(colorize(f"📝 {len(self.info)} TODOs/FIXMEs", Colors.BLUE))
        print(colorize("=" * 60, Colors.BOLD))

        return len(self.errors) == 0


def main():
    """Função principal"""
    print(colorize("🔍 Iniciando verificação de código...", Colors.BOLD))

    checker = CodeChecker()
    checker.check_python_files()
    checker.check_html_templates()
    checker.check_javascript_files()
    checker.check_css_files()

    success = checker.print_report()

    # Exit code baseado em erros
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

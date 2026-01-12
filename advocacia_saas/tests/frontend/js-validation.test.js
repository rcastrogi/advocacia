/**
 * Testes para validação de arquivos JavaScript
 * Verifica sintaxe e padrões comuns de erro
 */

const fs = require('fs');
const path = require('path');

// Diretório de arquivos JS
const JS_DIR = path.join(__dirname, '..', '..', 'app', 'static', 'js');

// Função para obter todos os arquivos JS
function getAllJSFiles(dir, files = []) {
    const items = fs.readdirSync(dir);
    for (const item of items) {
        const fullPath = path.join(dir, item);
        if (fs.statSync(fullPath).isDirectory()) {
            getAllJSFiles(fullPath, files);
        } else if (item.endsWith('.js')) {
            files.push(fullPath);
        }
    }
    return files;
}

describe('JavaScript Files Validation', () => {
    let jsFiles;

    beforeAll(() => {
        jsFiles = getAllJSFiles(JS_DIR);
    });

    test('should find JS files', () => {
        expect(jsFiles.length).toBeGreaterThan(0);
    });

    describe('Syntax Validation', () => {
        test.each(getAllJSFiles(JS_DIR))('file %s should have valid syntax', (filePath) => {
            const content = fs.readFileSync(filePath, 'utf8');
            
            // Verificar parênteses balanceados
            const openParens = (content.match(/\(/g) || []).length;
            const closeParens = (content.match(/\)/g) || []).length;
            expect(openParens).toBe(closeParens);

            // Verificar chaves balanceadas
            const openBraces = (content.match(/\{/g) || []).length;
            const closeBraces = (content.match(/\}/g) || []).length;
            expect(openBraces).toBe(closeBraces);

            // Verificar colchetes balanceados
            const openBrackets = (content.match(/\[/g) || []).length;
            const closeBrackets = (content.match(/\]/g) || []).length;
            expect(openBrackets).toBe(closeBrackets);
        });
    });

    describe('Common Error Patterns', () => {
        test.each(getAllJSFiles(JS_DIR))('file %s should not have common errors', (filePath) => {
            const content = fs.readFileSync(filePath, 'utf8');
            const fileName = path.basename(filePath);

            // Verificar uso de var (preferir let/const)
            const varUsages = (content.match(/\bvar\s+/g) || []).length;
            if (varUsages > 5) {
                console.warn(`${fileName}: ${varUsages} uses of 'var' found (consider let/const)`);
            }

            // Verificar == vs === (exceto null checks)
            const looseEquality = content.match(/[^=!]==[^=]/g) || [];
            if (looseEquality.length > 3) {
                console.warn(`${fileName}: ${looseEquality.length} uses of '==' (consider '===')`);
            }

            // Verificar console.log em produção
            const consoleLogs = (content.match(/console\.(log|debug)\(/g) || []).length;
            if (consoleLogs > 0) {
                console.warn(`${fileName}: ${consoleLogs} console.log/debug statements found`);
            }

            // Verificar eval (perigoso)
            expect(content).not.toMatch(/\beval\s*\(/);

            // Verificar innerHTML sem sanitização
            const innerHTMLUsages = (content.match(/\.innerHTML\s*=/g) || []).length;
            if (innerHTMLUsages > 5) {
                console.warn(`${fileName}: ${innerHTMLUsages} innerHTML assignments (check for XSS)`);
            }
        });
    });

    describe('Best Practices', () => {
        test.each(getAllJSFiles(JS_DIR))('file %s should follow best practices', (filePath) => {
            const content = fs.readFileSync(filePath, 'utf8');
            const fileName = path.basename(filePath);

            // Verificar funções muito longas (mais de 100 linhas)
            const functions = content.match(/function\s*\w*\s*\([^)]*\)\s*\{/g) || [];
            
            // Verificar try/catch em operações assíncronas
            const fetchCalls = (content.match(/\bfetch\s*\(/g) || []).length;
            const tryCatches = (content.match(/try\s*\{/g) || []).length;
            
            if (fetchCalls > 0 && tryCatches === 0) {
                console.warn(`${fileName}: ${fetchCalls} fetch calls without try/catch`);
            }

            // Verificar event listeners com funções anônimas (memory leak potential)
            const anonListeners = content.match(/addEventListener\s*\(\s*['"][^'"]+['"]\s*,\s*function\s*\(/g) || [];
            if (anonListeners.length > 10) {
                console.warn(`${fileName}: ${anonListeners.length} anonymous event listeners`);
            }
        });
    });

    describe('Security Patterns', () => {
        test.each(getAllJSFiles(JS_DIR))('file %s should be secure', (filePath) => {
            const content = fs.readFileSync(filePath, 'utf8');
            
            // Verificar document.write (perigoso)
            expect(content).not.toMatch(/document\.write\s*\(/);

            // Verificar uso direto de location (XSS potential)
            const locationUsages = content.match(/location\.(href|assign|replace)\s*=\s*[^;]+/g) || [];
            for (const usage of locationUsages) {
                // Se usa variável não sanitizada
                if (usage.match(/=\s*\w+/) && !usage.includes('encodeURI')) {
                    console.warn(`Potential XSS in location assignment: ${usage.substring(0, 50)}`);
                }
            }
        });
    });
});

describe('CSS Files Validation', () => {
    const CSS_DIR = path.join(__dirname, '..', '..', 'app', 'static', 'css');

    function getAllCSSFiles(dir, files = []) {
        if (!fs.existsSync(dir)) return files;
        const items = fs.readdirSync(dir);
        for (const item of items) {
            const fullPath = path.join(dir, item);
            if (fs.statSync(fullPath).isDirectory()) {
                getAllCSSFiles(fullPath, files);
            } else if (item.endsWith('.css')) {
                files.push(fullPath);
            }
        }
        return files;
    }

    test('CSS files should have balanced braces', () => {
        const cssFiles = getAllCSSFiles(CSS_DIR);
        
        for (const filePath of cssFiles) {
            const content = fs.readFileSync(filePath, 'utf8');
            const fileName = path.basename(filePath);

            const openBraces = (content.match(/\{/g) || []).length;
            const closeBraces = (content.match(/\}/g) || []).length;

            expect(openBraces).toBe(closeBraces);
        }
    });

    test('CSS files should not have !important overuse', () => {
        const cssFiles = getAllCSSFiles(CSS_DIR);
        
        for (const filePath of cssFiles) {
            const content = fs.readFileSync(filePath, 'utf8');
            const fileName = path.basename(filePath);

            const importants = (content.match(/!important/g) || []).length;
            
            if (importants > 20) {
                console.warn(`${fileName}: ${importants} uses of !important (consider refactoring)`);
            }
        }
    });
});

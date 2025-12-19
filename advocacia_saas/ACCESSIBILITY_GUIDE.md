# 🌟 Guia de Acessibilidade do Petitio

## Visão Geral

O Petitio implementa recursos abrangentes de acessibilidade seguindo as diretrizes **WCAG 2.1 Level AA/AAA**, garantindo que o sistema seja utilizável por pessoas com diferentes necessidades, incluindo deficiências visuais, motoras e cognitivas.

---

## 🎨 Recursos Visuais

### 1. Controle de Tamanho de Fonte
- **4 níveis de tamanho**: Pequena, Normal, Grande, Muito Grande
- **Persistência**: As preferências são salvas automaticamente no navegador
- **Como usar**: 
  - Clique no botão "ACESSIBILIDADE" no canto direito da tela
  - Selecione o tamanho de fonte desejado
  - A mudança é aplicada instantaneamente em todo o sistema

### 2. Modo de Alto Contraste
- **Esquema de cores otimizado**: Preto, branco e amarelo para máxima legibilidade
- **Contraste WCAG AAA**: Garante proporções de contraste superiores a 7:1
- **Como usar**:
  - Abra a barra de acessibilidade
  - Clique em "Alto Contraste"
  - O modo permanece ativo até ser desativado

### 3. Cores Otimizadas (Modo Normal)
- **Títulos**: #f0c8a0 (contraste 5.2:1 - WCAG AA)
- **Texto**: #f8f9fa (contraste 14:1 - WCAG AAA)
- **Subtítulos**: #e8e8e8 (contraste 12:1 - WCAG AAA)
- **Background**: Gradientes otimizados para legibilidade

---

## ⌨️ Navegação por Teclado

### Atalhos Globais
| Atalho | Função |
|--------|--------|
| `Alt + 1` | Ir para página inicial |
| `Alt + 2` | Ir para Dashboard |
| `Alt + 3` | Ir para Clientes |
| `Alt + H` | Abrir ajuda de atalhos |
| `Tab` | Navegar para próximo elemento |
| `Shift + Tab` | Navegar para elemento anterior |
| `Esc` | Fechar modais e diálogos |
| `Enter` | Ativar botões e links |

### Skip Links
- Pressione `Tab` na primeira posição da página para revelar o link "Pular para o conteúdo principal"
- Pressione `Enter` para pular diretamente ao conteúdo, ignorando a navegação

### Indicadores Visuais de Foco
- **Borda azul brilhante**: Indica o elemento atualmente focado
- **Sombra luminosa**: Melhora a visibilidade do foco
- **Sempre visível**: Não desaparece ao usar o teclado

---

## 🔊 Suporte a Leitores de Tela

### Compatibilidade
- ✅ **NVDA** (Windows)
- ✅ **JAWS** (Windows)
- ✅ **VoiceOver** (macOS/iOS)
- ✅ **TalkBack** (Android)
- ✅ **Narrator** (Windows)

### Recursos para Leitores de Tela
1. **Anúncios de Ações**
   - Confirmações de salvamento
   - Mensagens de erro
   - Mudanças de estado do sistema
   - Carregamento de dados

2. **Atributos ARIA**
   - `aria-label`: Descrições acessíveis para todos os botões
   - `aria-required`: Indica campos obrigatórios
   - `aria-invalid`: Sinaliza erros de validação
   - `aria-live`: Região de anúncios dinâmicos
   - `aria-expanded`: Estado de menus e painéis

3. **Estrutura Semântica**
   - Tags HTML5 apropriadas (`<main>`, `<nav>`, `<aside>`)
   - Hierarquia de cabeçalhos (`<h1>` a `<h6>`)
   - Rótulos descritivos para formulários
   - Tabelas com `<caption>` e `scope`

---

## 📝 Formulários Acessíveis

### Validação
- **Mensagens claras**: Erros explicativos em linguagem simples
- **Indicadores visuais**: Bordas vermelhas em campos inválidos
- **Anúncios de erro**: Leitores de tela são notificados automaticamente
- **Dicas inline**: Orientações sobre o formato esperado

### Campos de Busca de CEP
- **Bloqueio automático**: Após buscar o CEP, os campos são travados
- **Feedback visual**: Cursor "not-allowed" e cor acinzentada
- **Desbloqueio inteligente**: Alterar o CEP libera os campos novamente
- **Alerta de proteção**: Notificação ao tentar editar campos bloqueados

---

## 🎯 Áreas de Toque Aumentadas

- **Mínimo de 44x44 pixels**: Todos os botões e links seguem as diretrizes de acessibilidade móvel
- **Espaçamento adequado**: Previne cliques acidentais
- **Responsive**: Funciona bem em dispositivos móveis e desktop

---

## 🌐 Internacionalização

- **Idioma principal**: Português (pt-BR)
- **Atributo lang**: Definido corretamente para leitores de tela
- **Formatação de data**: Padrão brasileiro (dd/mm/aaaa)

---

## ⚙️ Como Ativar os Recursos

### Desktop
1. Localize o botão **"ACESSIBILIDADE"** na lateral direita da tela
2. Clique para abrir a barra de controles
3. Selecione as opções desejadas
4. Suas preferências serão salvas automaticamente

### Teclado
1. Pressione `Tab` até chegar ao botão de acessibilidade
2. Pressione `Enter` para abrir
3. Use `Tab` para navegar pelos controles
4. Pressione `Esc` para fechar

### Leitores de Tela
1. O leitor anunciará "Abrir barra de acessibilidade"
2. Ative o botão
3. Navegue pelos controles com as teclas de seta
4. As mudanças serão anunciadas automaticamente

---

## 🎬 Animações e Movimento Reduzido

O sistema respeita as preferências do sistema operacional:
- **`prefers-reduced-motion`**: Desativa animações automáticas
- **Transições suaves**: Opcionais e podem ser desabilitadas
- **Sem auto-play**: Nenhum conteúdo se move automaticamente

---

## 📊 Conformidade WCAG 2.1

### Level AA (Mínimo)
- ✅ Contraste de cores (1.4.3)
- ✅ Redimensionamento de texto (1.4.4)
- ✅ Navegação por teclado (2.1.1)
- ✅ Identificação de entrada (3.3.2)
- ✅ Rótulos ou instruções (3.3.2)

### Level AAA (Avançado)
- ✅ Contraste aprimorado (1.4.6)
- ✅ Imagens de texto (1.4.9)
- ✅ Identificação de contexto (3.3.4)
- ✅ Prevenção de erros (3.3.6)

---

## 🛠️ Tecnologias de Acessibilidade Utilizadas

### CSS
- `accessibility.css`: Estilos para modo de alto contraste
- `style.css`: Cores otimizadas e responsivas
- Media queries para `prefers-reduced-motion`

### JavaScript
- `accessibility.js`: Controle de fonte, contraste e navegação
- Gerenciamento de foco para modais
- Sistema de anúncios para leitores de tela
- Persistência de preferências com localStorage

### HTML5
- Marcação semântica (`<main>`, `<nav>`, `<aside>`)
- Atributos ARIA apropriados
- Skip links para navegação rápida
- Meta tags descritivas

---

## 📞 Suporte e Feedback

Se você encontrar barreiras de acessibilidade ou tiver sugestões de melhoria:

- **Email**: acessibilidade@petitio.com.br
- **Telefone**: (11) 9999-9999
- **Resposta**: Em até 48 horas úteis

---

## 🏆 Certificações e Padrões

O Petitio segue:
- ✅ **WCAG 2.1 Level AA/AAA** (Web Content Accessibility Guidelines)
- ✅ **Lei Brasileira de Inclusão** (LBI - Lei nº 13.146/2015)
- ✅ **eMAG** (Modelo de Acessibilidade em Governo Eletrônico)
- ✅ **Section 508** (Estados Unidos)

---

## 📚 Recursos Adicionais

### Para Usuários
- [Guia de uso do NVDA](https://www.nvaccess.org/get-help/)
- [VoiceOver no macOS](https://support.apple.com/pt-br/guide/voiceover/welcome/mac)
- [Atalhos de teclado do navegador](https://support.google.com/chrome/answer/157179?hl=pt-BR)

### Para Desenvolvedores
- [COLOR_GUIDE.md](./COLOR_GUIDE.md): Análise detalhada das cores
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Web Accessibility](https://developer.mozilla.org/pt-BR/docs/Web/Accessibility)

---

## 🔄 Atualizações

**Última atualização**: Janeiro 2025
**Versão**: 1.0.0

---

*Petitio - Inclusão e acessibilidade para todos os advogados* 🌟

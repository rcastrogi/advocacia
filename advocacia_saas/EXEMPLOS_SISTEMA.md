# 📋 Exemplos do Sistema de Petições Genérico

Este documento demonstra como usar o sistema de petições genérico implementado, com exemplos práticos de diferentes tipos de ação.

## 🚀 Deploy e Inicialização

### ✅ Exemplos Automáticos no Deploy

Os exemplos são **criados automaticamente** durante o primeiro deploy da aplicação:

1. **Verificação:** O sistema verifica se já existem tipos de petição no banco
2. **Criação:** Se estiver vazio, executa automaticamente:
   - `create_real_case_examples.py` - Cria tipos de petição realistas
   - `create_real_case_templates.py` - Cria templates jurídicos
3. **Resultado:** 20 tipos de petição prontos para uso

### 🔄 Comportamento em Deploys Seguintes

- **Deploy novo:** Exemplos são criados automaticamente
- **Deploy existente:** Exemplos são preservados (não recriados)
- **Desenvolvimento:** Scripts podem ser executados manualmente

### 📊 Exibição na Página Principal

Todos os tipos criados aparecem automaticamente na seção "Petições Disponíveis" da página inicial, incluindo:

- **6 tipos realistas** com cenários reais do direito brasileiro
- **Templates jurídicos** completos e profissionais
- **Formulários dinâmicos** totalmente configuráveis
- **Preços competitivos** baseados no mercado

## 🎯 Tipos de Petição Disponíveis

### 1. **Ação de Alimentos** (`/dynamic/acao-de-alimentos`)
**Seções incluídas:**
- Cabeçalho do Processo
- Qualificação das Partes
- Dos Fatos
- Do Pedido de Alimentos *(seção específica)*
- Do Direito
- Dos Pedidos
- Do Valor da Causa
- Assinatura

**Campos específicos:**
- Tipo de alimentos (provisórios/definitivos/provisórios e definitivos)
- Valor pretendido
- Justificativa do valor

### 2. **Ação de Divórcio Litigioso** (`/dynamic/acao-de-divorcio-litigioso`)
**Seções incluídas:**
- Cabeçalho do Processo
- Qualificação das Partes
- Do Regime de Bens *(seção específica)*
- Dos Fatos
- Do Direito
- Dos Pedidos
- Do Valor da Causa
- Assinatura

**Campos específicos:**
- Regime de casamento
- Data do casamento
- Pacto antenupcial (sim/não)

### 3. **Reclamação Trabalhista** (`/dynamic/reclamacao-trabalhista`)
**Seções incluídas:**
- Cabeçalho do Processo
- Qualificação das Partes
- Da Reclamação Trabalhista *(seção específica)*
- Dos Fatos
- Do Direito
- Dos Pedidos
- Do Valor da Causa
- Assinatura

**Campos específicos:**
- Data de admissão/demissão
- Cargo e salário
- Horário de trabalho
- Motivo da reclamação

### 4. **Ação de Cobrança** (`/dynamic/acao-de-cobranca`)
**Seções incluídas:**
- Cabeçalho do Processo
- Qualificação das Partes
- Da Cobrança *(seção específica)*
- Dos Fatos
- Do Direito
- Dos Pedidos
- Do Valor da Causa
- Assinatura

**Campos específicos:**
- Valor cobrado
- Data de vencimento
- Origem da dívida

## 🔧 Como Criar Novos Tipos de Petição

### Passo 1: Criar Seções Personalizadas
Acesse `/admin/petitions/sections/new` e crie seções com campos JSON:

```json
[
  {
    "name": "valor_indenizacao",
    "label": "Valor da Indenização",
    "type": "number",
    "required": true,
    "size": "col-md-6",
    "placeholder": "0.00"
  },
  {
    "name": "tipo_dano",
    "label": "Tipo de Dano",
    "type": "select",
    "required": true,
    "size": "col-md-6",
    "options": [
      {"value": "material", "label": "Dano Material"},
      {"value": "moral", "label": "Dano Moral"},
      {"value": "estetico", "label": "Dano Estético"}
    ]
  }
]
```

### Passo 2: Criar Tipo de Petição
Acesse `/admin/petitions/types/new`:
- Nome: "Ação de Indenização por Danos Morais"
- Slug: "acao-indenizacao-danos-morais"
- Categoria: Cível
- Marcar: "Usar formulário dinâmico"

### Passo 3: Configurar Seções
Em `/admin/petitions/types/{id}/sections`:
- Adicionar seções existentes
- Ordenar por arrastar e soltar
- Definir obrigatoriedade

### Passo 4: Criar Template
Crie um template Jinja2 que use as variáveis dos campos:

```jinja2
<h2>II - DO DANO</h2>
<p>O autor sofreu {{ tipo_dano }} no valor de R$ {{ valor_indenizacao }}.</p>
```

## 📝 Exemplos de Preenchimento

### Exemplo 1: Ação de Alimentos

**Cabeçalho:**
- Foro: Foro Central da Comarca de São Paulo
- Vara: Vara de Família e Sucessões

**Qualificação do Autor:**
- Nome: MARIA SILVA
- CPF: 123.456.789-00
- Endereço: Rua das Flores, 123, São Paulo/SP

**Qualificação do Réu:**
- Nome: JOSÉ SILVA
- CPF: 987.654.321-00
- Endereço: Av. Paulista, 1000, São Paulo/SP

**Pedido de Alimentos:**
- Tipo: Provisórios e definitivos
- Valor: R$ 2.500,00
- Justificativa: O réu aufere renda mensal de R$ 8.000,00 e deve contribuir com 30% para o sustento do filho menor.

### Exemplo 2: Reclamação Trabalhista

**Reclamação Trabalhista:**
- Data admissão: 01/01/2020
- Data demissão: 15/12/2023
- Cargo: Analista de Sistemas
- Salário: R$ 5.000,00
- Horário: 08:00 às 18:00
- Motivo: Não pagamento de horas extras, férias não gozadas, FGTS não depositado.

## 🎨 Personalização Visual

### Ícones Disponíveis
- `fa-gavel` - Ações judiciais
- `fa-utensils` - Alimentos
- `fa-heart-broken` - Família/divórcio
- `fa-briefcase` - Trabalhista
- `fa-money-bill` - Cobrança
- `fa-balance-scale` - Direito

### Cores Bootstrap
- `primary` (azul) - Geral
- `success` (verde) - Família/alimentos
- `danger` (vermelho) - Divórcio/conflitos
- `warning` (amarelo) - Trabalhista
- `info` (ciano) - Cobrança
- `secondary` (cinza) - Administrativo

## 📊 Gerenciamento Administrativo

### Dashboard: `/admin/petitions`
- Visão geral de tipos e seções
- Estatísticas de uso
- Links rápidos para criação

### Tipos de Petição: `/admin/petitions/types`
- Lista todos os tipos
- CRUD completo
- Configuração de seções por tipo

### Seções: `/admin/petitions/sections`
- Biblioteca de seções reutilizáveis
- Campos JSON configuráveis
- Preview em tempo real

## 🚀 Próximos Passos

Para expandir o sistema:

1. **Criar mais seções especializadas:**
   - Responsabilidade civil
   - Consumidor
   - Previdenciário
   - Tributário

2. **Adicionar validações avançadas:**
   - CPF/CNPJ
   - Datas coerentes
   - Valores mínimos/máximos

3. **Templates condicionais:**
   - Mostrar/ocultar seções baseadas em respostas
   - Lógica condicional nos templates

4. **Integração com APIs:**
   - Consulta de processos
   - Validação de documentos
   - Cálculos automáticos

## 💡 Dicas de Uso

- **Mantenha seções genéricas** para reutilização máxima
- **Use nomes descritivos** nos campos para facilitar o preenchimento
- **Valide templates** testando com dados reais
- **Documente campos especiais** com placeholders informativos
- **Agrupe seções lógicas** por ordem jurídica comum

O sistema agora permite criar qualquer tipo de petição jurídica sem modificar código, apenas configurando seções e templates através da interface administrativa!
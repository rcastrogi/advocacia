# Sistema de Seções Dinâmicas para Petições

Este documento explica como funciona o novo sistema de seções dinâmicas para criação de petições.

## Visão Geral

O sistema permite criar tipos de petições dinâmicas onde o usuário pode configurar quais seções (como "Autor", "Réu", "Testemunha", etc.) estarão disponíveis em cada tipo de petição.

## Interface Visual de Campos

### 🎨 **Nova Interface Intuitiva**

A partir de agora, você pode criar e editar campos das seções de forma visual, sem precisar editar JSON diretamente!

#### **Como Criar uma Seção:**

1. **Acesse Admin → Seções de Petição**
2. **Clique em "Nova Seção"**
3. **Preencha os dados básicos:**
   - Nome da seção
   - Slug (gerado automaticamente)
   - Ícone e cor
   - Descrição

4. **Adicione Campos Visualmente:**
   - Clique em **"Adicionar Campo"**
   - Configure cada campo:
     - **Nome Interno:** Identificador único (ex: `autor_nome`)
     - **Rótulo:** Texto que aparece (ex: "Nome do Autor")
     - **Tipo:** Texto, Área de Texto, Lista, Email, Número, Data, Telefone
     - **Largura:** 25%, 33%, 50%, 67%, 100%
     - **Obrigatório:** Marque se o campo é obrigatório
     - **Texto de Exemplo:** Placeholder do campo

5. **Para Campos do Tipo Lista:**
   - Adicione opções clicando em **"Adicionar Opção"**
   - Configure Valor e Rótulo para cada opção

6. **Preview em Tempo Real:**
   - Veja como os campos ficarão no formulário
   - Visualize validações e tamanhos

### 📝 **Tipos de Campos Disponíveis**

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| **Texto** | Campo de texto simples | Nome, Endereço |
| **Área de Texto** | Campo para textos longos | Qualificação completa |
| **Lista de Opções** | Dropdown com opções | Tipo de pessoa, Estado civil |
| **Email** | Campo específico para emails | Email de contato |
| **Número** | Campo numérico | Valor da causa, Idade |
| **Data** | Seletor de data | Data de nascimento |
| **Telefone** | Campo para telefone | Telefone de contato |

## Seções Pré-definidas

Foram criadas **22 seções abrangentes** organizadas por categoria:

### 1. **Partes do Processo**
- **Autor/Peticionário**: Dados completos da pessoa que propõe a ação (física/jurídica)
- **Réu/Acusado**: Dados da pessoa contra quem se propõe a ação
- **Testemunha**: Dados das testemunhas com relação às partes
- **Terceiro Interessado**: Fiadores, avalistas, proprietários, etc.
- **Representante Legal**: Tutores, curadores, procuradores para menores/incapazes

### 2. **Dados do Processo**
- **Dados do Processo**: Número, vara, comarca, valor da causa, juiz, rito processual

### 3. **Conteúdo da Petição**
- **Fatos**: Descrição detalhada dos fatos ocorridos
- **Fundamentação Jurídica**: Base legal, legislação e jurisprudência
- **Pedidos**: Pedidos formulados, liminar e antecipação de tutela
- **Valor da Causa**: Cálculo detalhado do valor atribuído

### 4. **Informações Específicas por Área**

#### **Dados Contratuais**
- Tipo de contrato, número, data, valor, prazo, objeto, cláusulas importantes

#### **Dados Trabalhistas**
- Cargo, admissão/demissão, salário, carga horária, vínculo, benefícios, verbas rescisórias

#### **Dados Familiares**
- Tipo de ação, casamento, regime, filhos, guarda, pensão alimentícia

#### **Dados Criminais**
- Tipo de crime, artigo penal, data/local, circunstâncias, testemunhas, provas

#### **Dados Previdenciários**
- Benefício pretendido, NB, concessão, contribuição, carência, salário

#### **Dados Tributários**
- Tipo de tributo, período, valor, auto de infração, legislação

#### **Dados Ambientais**
- Tipo de dano, local, área afetada, espécies, licenças, multas, reparação

#### **Dados Consumeristas**
- Relação de consumo, produto/serviços, compra, defeito, pedidos

### 5. **Documentos e Anexos**
- **Documentos Apresentados**: Obrigatórios, comprobatórios, certidões, outros

### 6. **Informações Adicionais**
- **Pedido de Urgência**: Liminar, tutela antecipada, fundamentos, medidas
- **Honorários Advocatícios**: Contratual, sucumbência, base de cálculo
- **Custas Processuais**: Valores, responsabilidade, isenção

## Como Configurar um Tipo de Petição

### 1. **Acesse o Admin**
- Vá para Admin → Tipos de Petição
- Selecione um tipo de petição existente ou crie um novo

### 2. **Configure as Seções**
- Clique em "Seções" para o tipo desejado
- Adicione seções disponíveis clicando em "Adicionar Seção"
- Configure a ordem arrastando as seções
- Marque seções como obrigatórias ou expandidas por padrão

### 3. **Personalização de Campos**
Para cada seção adicionada, você pode:
- **Ordem**: Define a sequência em que as seções aparecem no formulário
- **Obrigatória**: Se marcada, a seção deve ser preenchida
- **Expandida**: Se marcada, a seção começa aberta no formulário

## Criação das Seções

Para criar todas as seções pré-definidas, execute:

```bash
python create_comprehensive_sections.py
```

Este comando criará todas as 22 seções templates no banco de dados.

## Exemplos de Configuração

### **Ação de Cobrança Contratual**
1. Autor/Peticionário (obrigatório)
2. Réu/Acusado (obrigatório)
3. Dados do Processo (obrigatório)
4. Dados Contratuais (obrigatório)
5. Fatos (obrigatório)
6. Fundamentação Jurídica (obrigatório)
7. Valor da Causa (obrigatório)
8. Pedidos (obrigatório)
9. Documentos Apresentados (opcional)

### **Ação Trabalhista**
1. Autor/Peticionário (obrigatório)
2. Réu/Acusado (obrigatório)
3. Dados do Processo (obrigatório)
4. Dados Trabalhistas (obrigatório)
5. Fatos (obrigatório)
6. Fundamentação Jurídica (obrigatório)
7. Pedidos (obrigatório)
8. Valor da Causa (obrigatório)
9. Honorários Advocatícios (opcional)

### **Ação de Família - Divórcio**
1. Autor/Peticionário (obrigatório)
2. Réu/Acusado (obrigatório)
3. Dados do Processo (obrigatório)
4. Dados Familiares (obrigatório)
5. Fatos (obrigatório)
6. Fundamentação Jurídica (obrigatório)
7. Pedidos (obrigatório)
8. Valor da Causa (opcional)

## Uso no Frontend

O formulário dinâmico usa JavaScript (Alpine.js) para renderizar os campos baseado na configuração das seções. Os dados são salvos em JSON e podem ser usados nos templates de petição.

## Próximos Passos

- Implementar validação de campos obrigatórios
- Adicionar mais tipos de campos (checkbox, radio, file upload)
- Permitir personalização de campos por tipo de petição
- Criar interface para editar campos das seções
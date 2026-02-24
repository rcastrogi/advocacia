# Petitio Assinador - Agent Desktop para Certificado A3 (Smart Card)

App desktop leve que faz ponte entre o Petitio web e o certificado A3
do advogado (smart card via leitor OmniKey ou similar).

## Como funciona

1. O advogado instala o Petitio Assinador no Windows
2. O app roda na bandeja do sistema (system tray)
3. Detecta automaticamente o leitor de cartão e certificado
4. O Petitio web se comunica com o app via `localhost:7777`
5. Assinaturas acontecem dentro do smart card (chave privada nunca sai)

## Instalação (desenvolvimento)

```bash
pip install -r requirements.txt
python main.py
```

## Build (gerar instalador)

```bash
pip install pyinstaller
pyinstaller petitio_assinador.spec
```

O executável gerado estará em `dist/PetitioAssinador/`.

## Endpoints da API local

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/status` | Verifica se o agent está rodando + info do cartão |
| GET | `/certificados` | Lista certificados no smart card |
| POST | `/assinar` | Assina um PDF com o certificado A3 |
| POST | `/consultar` | Consulta processo no tribunal via certificado A3 |

## Segurança

- Aceita conexões apenas de `localhost` e `petitio.onrender.com`
- CORS restrito ao domínio do Petitio
- PIN do cartão é solicitado a cada operação de assinatura
- Nenhuma chave privada é transmitida — assinatura acontece no chip

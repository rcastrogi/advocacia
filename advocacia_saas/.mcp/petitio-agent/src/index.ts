import {
  Server,
  StdioServerTransport,
} from "@modelcontextprotocol/sdk/server/index.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

// Initialize MCP Server
const server = new Server({
  name: "petitio-code-agent",
  version: "1.0.0",
});

// Define tools que o agent oferece
const tools: Tool[] = [
  {
    name: "analyze_security",
    description:
      "Analisa código em busca de vulnerabilidades de segurança baseado nos padrões Petitio",
    inputSchema: {
      type: "object" as const,
      properties: {
        code: {
          type: "string",
          description: "Código a ser analisado",
        },
        language: {
          type: "string",
          enum: ["python", "javascript", "typescript"],
          description: "Linguagem do código",
        },
      },
      required: ["code", "language"],
    },
  },
  {
    name: "check_rate_limits",
    description:
      "Verifica se todas as rotas têm rate limiting configurado corretamente",
    inputSchema: {
      type: "object" as const,
      properties: {
        code: {
          type: "string",
          description: "Código Python com rotas Flask",
        },
      },
      required: ["code"],
    },
  },
  {
    name: "validate_decorators",
    description: "Valida se os decoradores estão na ordem correta",
    inputSchema: {
      type: "object" as const,
      properties: {
        code: {
          type: "string",
          description: "Código com decoradores",
        },
      },
      required: ["code"],
    },
  },
  {
    name: "check_xss",
    description: "Detecta vulnerabilidades potenciais de XSS no código",
    inputSchema: {
      type: "object" as const,
      properties: {
        code: {
          type: "string",
          description: "Código JavaScript/TypeScript a verificar",
        },
      },
      required: ["code"],
    },
  },
  {
    name: "check_input_sanitization",
    description:
      "Verifica se inputs estão sendo sanitizados corretamente",
    inputSchema: {
      type: "object" as const,
      properties: {
        code: {
          type: "string",
          description: "Código a verificar",
        },
        language: {
          type: "string",
          enum: ["python", "javascript"],
          description: "Linguagem do código",
        },
      },
      required: ["code", "language"],
    },
  },
  {
    name: "suggest_fix",
    description: "Sugere correções para código que viola os padrões Petitio",
    inputSchema: {
      type: "object" as const,
      properties: {
        issue: {
          type: "string",
          description: "Descrição do problema encontrado",
        },
        code: {
          type: "string",
          description: "Código problemático",
        },
      },
      required: ["issue", "code"],
    },
  },
];

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "analyze_security":
      return handleAnalyzeSecurity(args);
    case "check_rate_limits":
      return handleCheckRateLimits(args);
    case "validate_decorators":
      return handleValidateDecorators(args);
    case "check_xss":
      return handleCheckXss(args);
    case "check_input_sanitization":
      return handleCheckInputSanitization(args);
    case "suggest_fix":
      return handleSuggestFix(args);
    default:
      return {
        content: [
          {
            type: "text",
            text: `Tool ${name} not found`,
          },
        ],
      };
  }
});

function handleAnalyzeSecurity(args: Record<string, unknown>) {
  const code = args.code as string;
  const language = args.language as string;

  const issues: string[] = [];

  if (language === "python") {
    // Verificar rate limiting
    if (code.includes("@bp.route") && !code.includes("@limiter.limit")) {
      issues.push("❌ Rate limiting obrigatório está faltando em rotas");
    }

    // Verificar SQL Injection
    if (
      (code.includes('f"') || code.includes("f'")) &&
      code.includes("query")
    ) {
      issues.push(
        "❌ SQL Injection: Detectada string interpolation em query"
      );
    }

    // Verificar validação de JSON
    if (
      code.includes("request.get_json()") &&
      !code.includes("if not data")
    ) {
      issues.push("⚠️  JSON não validado após get_json()");
    }
  } else if (language === "javascript" || language === "typescript") {
    // Verificar XSS
    if (code.includes("innerHTML") && code.includes("${")) {
      issues.push("❌ XSS: innerHTML com interpolação detectada");
    }

    // Verificar CSRF
    if (
      code.includes("fetch") &&
      (code.includes("POST") || code.includes("PUT")) &&
      !code.includes("CSRFToken")
    ) {
      issues.push("⚠️  CSRF token ausente em método inseguro");
    }
  }

  const result =
    issues.length === 0
      ? "✅ Nenhum problema de segurança detectado"
      : issues.join("\n");

  return {
    content: [
      {
        type: "text",
        text: result,
      },
    ],
  };
}

function handleCheckRateLimits(args: Record<string, unknown>) {
  const code = args.code as string;

  const routes = code.match(/@bp\.route[^\n]*/g) || [];
  const issues: string[] = [];

  routes.forEach((route) => {
    // Verificar se a rota anterior tem @limiter.limit
    const routeIndex = code.indexOf(route);
    const prevContent = code.substring(Math.max(0, routeIndex - 200), routeIndex);

    if (!prevContent.includes("@limiter.limit")) {
      issues.push(`❌ ${route.trim()} - Sem rate limiting`);
    }
  });

  if (issues.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: "✅ Todas as rotas têm rate limiting configurado",
        },
      ],
    };
  }

  return {
    content: [
      {
        type: "text",
        text: `⚠️  ${issues.length} rota(s) sem rate limiting:\n${issues.join("\n")}`,
      },
    ],
  };
}

function handleValidateDecorators(args: Record<string, unknown>) {
  const code = args.code as string;

  const correctOrder = ["@limiter.limit", "@bp.route", "@login_required"];
  const issues: string[] = [];

  // Procurar por decoradores mal ordenados
  const decoratorLines = code
    .split("\n")
    .filter((line) => line.trim().startsWith("@"));

  for (let i = 0; i < decoratorLines.length - 1; i++) {
    const current = decoratorLines[i].trim();
    const next = decoratorLines[i + 1].trim();

    if (current.includes("@limiter") && next.includes("@login_required")) {
      issues.push(
        "⚠️  @login_required deveria vir após @bp.route, não antes de @limiter"
      );
    }
  }

  if (issues.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: "✅ Ordem dos decoradores está correta",
        },
      ],
    };
  }

  return {
    content: [
      {
        type: "text",
        text: issues.join("\n"),
      },
    ],
  };
}

function handleCheckXss(args: Record<string, unknown>) {
  const code = args.code as string;

  const issues: string[] = [];

  // Detectar innerHTML com interpolação
  if (code.includes("innerHTML") && code.includes("${")) {
    issues.push(
      "❌ innerHTML com template literals detectado - Risco de XSS"
    );
  }

  // Detectar onclick com strings
  if (code.includes('onclick=') && (code.includes('`') || code.includes('"'))) {
    issues.push("❌ onclick com strings dinâmicas - Use addEventListener()");
  }

  // Detectar eval() ou Function()
  if (code.includes("eval(") || code.includes("new Function(")) {
    issues.push("❌ eval() ou new Function() detectado - NUNCA usar!");
  }

  if (issues.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: "✅ Nenhuma vulnerabilidade XSS detectada",
        },
      ],
    };
  }

  return {
    content: [
      {
        type: "text",
        text: issues.join("\n"),
      },
    ],
  };
}

function handleCheckInputSanitization(args: Record<string, unknown>) {
  const code = args.code as string;
  const language = args.language as string;

  const issues: string[] = [];

  if (language === "python") {
    // Verificar se inputs são sanitizados
    if (code.includes("data.get(") && !code.includes("sanitize")) {
      issues.push(
        "⚠️  data.get() sem sanitização detectado - Use sanitize_code() ou sanitize_text()"
      );
    }

    if (code.includes("request.form.get") && !code.includes("sanitize")) {
      issues.push("⚠️  request.form.get() sem sanitização");
    }
  } else if (language === "javascript") {
    // Verificar manipulação DOM
    if (code.includes("document.write(") && code.includes("user")) {
      issues.push("❌ document.write() com dados do usuário - NUNCA usar");
    }

    if (code.includes(".innerHTML =") && code.includes("user")) {
      issues.push(
        "⚠️  .innerHTML com dados do usuário - Use .textContent ou createElement()"
      );
    }
  }

  if (issues.length === 0) {
    return {
      content: [
        {
          type: "text",
          text: "✅ Inputs parecem estar sendo sanitizados corretamente",
        },
      ],
    };
  }

  return {
    content: [
      {
        type: "text",
        text: issues.join("\n"),
      },
    ],
  };
}

function handleSuggestFix(args: Record<string, unknown>) {
  const issue = args.issue as string;
  const code = args.code as string;

  let suggestion = "";

  if (
    issue.toLowerCase().includes("rate limit") ||
    code.includes("@bp.route")
  ) {
    suggestion = `
**Correção para Rate Limiting:**

❌ Antes:
\`\`\`python
@bp.route("/api/users", methods=["POST"])
@login_required
def create_user():
    pass
\`\`\`

✅ Depois:
\`\`\`python
@limiter.limit(AUTH_API_LIMIT)  # SEMPRE primeiro
@bp.route("/api/users", methods=["POST"])
@login_required
def create_user():
    pass
\`\`\`
`;
  } else if (
    issue.toLowerCase().includes("xss") ||
    issue.toLowerCase().includes("innerhtml")
  ) {
    suggestion = `
**Correção para XSS:**

❌ Antes:
\`\`\`javascript
element.innerHTML = \`<div>\${userInput}</div>\`;
\`\`\`

✅ Depois:
\`\`\`javascript
element.textContent = userInput;
// Ou
const div = document.createElement('div');
div.textContent = userInput;
parent.appendChild(div);
\`\`\`
`;
  } else if (issue.toLowerCase().includes("csrf")) {
    suggestion = `
**Correção para CSRF:**

❌ Antes:
\`\`\`javascript
fetch('/api/endpoint', {
    method: 'POST',
    body: JSON.stringify(data)
});
\`\`\`

✅ Depois:
\`\`\`javascript
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(data)
});
\`\`\`
`;
  } else if (issue.toLowerCase().includes("sanitiz")) {
    suggestion = `
**Correção para Sanitização:**

❌ Antes:
\`\`\`python
data = request.get_json()
name = data.get("name")
\`\`\`

✅ Depois:
\`\`\`python
data = request.get_json()
if not data:
    return jsonify({"success": False}), 400

name = sanitize_text(data.get("name", ""))
\`\`\`
`;
  }

  return {
    content: [
      {
        type: "text",
        text: suggestion || "Não consegui sugerir uma correção específica",
      },
    ],
  };
}

// Start the server
const transport = new StdioServerTransport();
server.connect(transport);

console.error("Petitio Code Agent MCP Server iniciado");

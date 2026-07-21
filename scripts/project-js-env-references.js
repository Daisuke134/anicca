#!/usr/bin/env node
"use strict";

// Parse one JS/TS source file and emit only safe import/reference coordinates.
// Source text, values, and snippets never cross this projection boundary.
const path = require("path");
const fs = require("fs");

const [typescriptModule, sourcePath, sourceFdText] = process.argv.slice(2);
if (!typescriptModule || !sourcePath || !/^\d+$/.test(sourceFdText || "")) {
  process.stderr.write("AST projection arguments required\n");
  process.exit(2);
}

const ts = global.__credentialInventoryTypeScript || require(typescriptModule);
const absoluteSourcePath = path.resolve(sourcePath);
const sourceText = fs.readFileSync(Number(sourceFdText), "utf8");
const compilerOptions = {
  allowJs: true,
  checkJs: true,
  noEmit: true,
  noLib: true,
  noResolve: true,
  target: ts.ScriptTarget.Latest,
  types: [],
};
const sourceFromFd = ts.createSourceFile(
  absoluteSourcePath,
  sourceText,
  ts.ScriptTarget.Latest,
  true,
  ts.getScriptKindFromFileName(absoluteSourcePath),
);
const compilerHost = ts.createCompilerHost(compilerOptions, true);
compilerHost.fileExists = (fileName) => path.resolve(fileName) === absoluteSourcePath;
compilerHost.readFile = (fileName) => (
  path.resolve(fileName) === absoluteSourcePath ? sourceText : undefined
);
compilerHost.getSourceFile = (fileName) => (
  path.resolve(fileName) === absoluteSourcePath ? sourceFromFd : undefined
);
const program = ts.createProgram([absoluteSourcePath], compilerOptions, compilerHost);
const sourceFile = program.getSourceFile(absoluteSourcePath);
if (!sourceFile || program.getSyntacticDiagnostics(sourceFile).length > 0) {
  process.stderr.write("AST parse failed\n");
  process.exit(2);
}
const checker = program.getTypeChecker();

const credentialHint = /(?:KEY|TOKEN|SECRET|PASSWORD|PRIVATE|WEBHOOK|CREDENTIAL|AUTH|ACCOUNT_SID|DATABASE_URL|REDIS_URL|MONGODB_URI)/;
const credentialName = /^[A-Z][A-Z0-9_]*$/;
const PROCESS = Object.freeze({ kind: "process" });
const ENVIRONMENT = Object.freeze({ kind: "environment" });
const UNKNOWN = Object.freeze({ kind: "unknown" });
const references = [];
const imports = [];
const functionInfos = new Map();
const functionNodes = new Map();
const functionAtoms = new Map();
const literalAtoms = new Map();
const parameterAtoms = new Map();
const assignments = [];
const globalValues = new Map();
let unresolvedDynamicEnv = false;
let unresolvedImport = false;

function lineOf(node) {
  return sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1;
}

function stringValue(node) {
  return ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)
    ? node.text
    : null;
}

function symbolAt(node) {
  if (!node) return null;
  let symbol = checker.getSymbolAtLocation(node);
  if (symbol && symbol.flags & ts.SymbolFlags.Alias) {
    try {
      symbol = checker.getAliasedSymbol(symbol);
    } catch (_) {
      return null;
    }
  }
  return symbol || null;
}

function functionSymbol(node) {
  if (ts.isFunctionDeclaration(node) && node.name) return symbolAt(node.name);
  if (
    (ts.isArrowFunction(node) || ts.isFunctionExpression(node))
    && ts.isVariableDeclaration(node.parent)
    && ts.isIdentifier(node.parent.name)
  ) return symbolAt(node.parent.name);
  return null;
}

function isGlobalProcess(node) {
  if (!ts.isIdentifier(node) || node.text !== "process") return false;
  const symbol = symbolAt(node);
  if (!symbol) return true;
  return !(symbol.declarations || []).some(
    (declaration) => (
      declaration.getSourceFile() === sourceFile
      && !(
        ts.isIdentifier(declaration)
        && ts.isPropertyAccessExpression(declaration.parent)
        && declaration.parent.expression === declaration
      )
    ),
  );
}

function functionAtom(symbol) {
  if (!functionAtoms.has(symbol)) {
    functionAtoms.set(symbol, Object.freeze({ kind: "function", symbol }));
  }
  return functionAtoms.get(symbol);
}

function literalAtom(node, value) {
  const key = node.getStart(sourceFile);
  if (!literalAtoms.has(key)) {
    literalAtoms.set(key, Object.freeze({ kind: "literal", value, node }));
  }
  return literalAtoms.get(key);
}

function parameterAtom(info, index) {
  const key = `${info.node.getStart(sourceFile)}:${index}`;
  if (!parameterAtoms.has(key)) {
    parameterAtoms.set(key, Object.freeze({ kind: "parameter", info, index }));
  }
  return parameterAtoms.get(key);
}

function union(...values) {
  const result = new Set();
  for (const value of values) {
    if (!value) continue;
    for (const atom of value) result.add(atom);
  }
  return result;
}

function merge(target, value) {
  let changed = false;
  for (const atom of value) {
    if (!target.has(atom)) {
      target.add(atom);
      changed = true;
    }
  }
  return changed;
}

function addReference(name, node) {
  if (credentialName.test(name) && credentialHint.test(name)) {
    references.push({ reference_name: name, line: lineOf(node) });
  }
}

function collectStructure(node) {
  if (
    ts.isFunctionDeclaration(node)
    || ts.isArrowFunction(node)
    || ts.isFunctionExpression(node)
  ) {
    const lexicalSymbol = functionSymbol(node);
    const identity = lexicalSymbol || node;
    const info = {
      node,
      symbol: identity,
      parameterSymbols: node.parameters.map((parameter) => (
        ts.isIdentifier(parameter.name) ? symbolAt(parameter.name) : null
      )),
    };
    functionInfos.set(identity, info);
    functionNodes.set(node, info);
    if (lexicalSymbol) {
      globalValues.set(lexicalSymbol, new Set([functionAtom(lexicalSymbol)]));
    }
  }
  if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
    const symbol = symbolAt(node.name);
    if (symbol) assignments.push({ symbol, expression: node.initializer });
  }
  if (
    ts.isBinaryExpression(node)
    && node.operatorToken.kind === ts.SyntaxKind.EqualsToken
    && ts.isIdentifier(node.left)
  ) {
    const symbol = symbolAt(node.left);
    if (symbol) assignments.push({ symbol, expression: node.right });
  }
  ts.forEachChild(node, collectStructure);
}

collectStructure(sourceFile);

function valuesForIdentifier(node, locals) {
  if (isGlobalProcess(node)) return new Set([PROCESS]);
  const symbol = symbolAt(node);
  if (!symbol) return new Set([UNKNOWN]);
  if (locals.has(symbol)) return locals.get(symbol);
  if (globalValues.has(symbol)) return globalValues.get(symbol);
  if (functionInfos.has(symbol)) return new Set([functionAtom(symbol)]);
  return new Set([UNKNOWN]);
}

function evaluateProperty(node, locals, effects, stack) {
  const base = evaluateExpression(node.expression, locals, effects, stack);
  if (node.name.text === "env" && base.has(PROCESS)) {
    return base.has(UNKNOWN)
      ? new Set([ENVIRONMENT, UNKNOWN])
      : new Set([ENVIRONMENT]);
  }
  if (base.has(ENVIRONMENT)) {
    if (effects) {
      addReference(node.name.text, node);
      if (base.has(UNKNOWN)) unresolvedDynamicEnv = true;
    }
    return new Set([UNKNOWN]);
  }
  return new Set([UNKNOWN]);
}

function evaluateElement(node, locals, effects, stack) {
  const base = evaluateExpression(node.expression, locals, effects, stack);
  const key = evaluateExpression(node.argumentExpression, locals, effects, stack);
  const literalKeys = [...key].filter((atom) => atom.kind === "literal");
  if (base.has(PROCESS) && literalKeys.some((atom) => atom.value === "env")) {
    return base.has(UNKNOWN) || key.has(UNKNOWN)
      ? new Set([ENVIRONMENT, UNKNOWN])
      : new Set([ENVIRONMENT]);
  }
  if (base.has(ENVIRONMENT)) {
    if (effects) {
      for (const atom of literalKeys) addReference(atom.value, atom.node || node);
      if (key.has(UNKNOWN) || base.has(UNKNOWN)) unresolvedDynamicEnv = true;
    }
    return new Set([UNKNOWN]);
  }
  return new Set([UNKNOWN]);
}

function evaluateCall(node, locals, effects, stack) {
  const callee = evaluateExpression(node.expression, locals, effects, stack);
  const argumentsValues = node.arguments.map(
    (argument) => evaluateExpression(argument, locals, effects, stack),
  );
  const callable = [...callee].filter((atom) => atom.kind === "function");
  let result = new Set();
  for (const atom of callable) {
    result = union(
      result,
      invokeFunction(functionInfos.get(atom.symbol), argumentsValues, effects, stack),
    );
  }
  const environmentArgument = argumentsValues.some((value) => value.has(ENVIRONMENT));
  if (
    effects
    && environmentArgument
    && (callable.length === 0 || callee.has(UNKNOWN))
  ) {
    unresolvedDynamicEnv = true;
  }
  return result.size > 0 ? result : new Set([UNKNOWN]);
}

function evaluateExpression(node, locals, effects, stack) {
  if (!node) return new Set();
  if (ts.isIdentifier(node)) return valuesForIdentifier(node, locals);
  const literal = stringValue(node);
  if (literal !== null) return new Set([literalAtom(node, literal)]);
  if (ts.isPropertyAccessExpression(node)) {
    return evaluateProperty(node, locals, effects, stack);
  }
  if (ts.isElementAccessExpression(node)) {
    return evaluateElement(node, locals, effects, stack);
  }
  if (ts.isConditionalExpression(node)) {
    evaluateExpression(node.condition, locals, effects, stack);
    return union(
      evaluateExpression(node.whenTrue, locals, effects, stack),
      evaluateExpression(node.whenFalse, locals, effects, stack),
    );
  }
  if (ts.isCallExpression(node)) return evaluateCall(node, locals, effects, stack);
  if (ts.isNewExpression(node)) {
    for (const argument of node.arguments || []) {
      evaluateExpression(argument, locals, effects, stack);
    }
    return new Set([UNKNOWN]);
  }
  if (ts.isObjectLiteralExpression(node)) {
    for (const property of node.properties) {
      if (ts.isPropertyAssignment(property)) {
        evaluateExpression(property.initializer, locals, effects, stack);
      } else if (ts.isSpreadAssignment(property)) {
        evaluateExpression(property.expression, locals, effects, stack);
      }
    }
    return new Set([UNKNOWN]);
  }
  if (ts.isArrayLiteralExpression(node)) {
    for (const element of node.elements) {
      evaluateExpression(element, locals, effects, stack);
    }
    return new Set([UNKNOWN]);
  }
  if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
    const info = functionNodes.get(node);
    return info ? new Set([functionAtom(info.symbol)]) : new Set([UNKNOWN]);
  }
  if (
    ts.isParenthesizedExpression(node)
    || ts.isAsExpression(node)
    || ts.isTypeAssertionExpression(node)
    || ts.isNonNullExpression(node)
  ) return evaluateExpression(node.expression, locals, effects, stack);
  if (ts.isBinaryExpression(node)) {
    if (node.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const value = evaluateExpression(node.right, locals, effects, stack);
      if (ts.isIdentifier(node.left)) {
        const symbol = symbolAt(node.left);
        if (symbol && locals.has(symbol)) merge(locals.get(symbol), value);
      }
      return value;
    }
    return union(
      evaluateExpression(node.left, locals, effects, stack),
      evaluateExpression(node.right, locals, effects, stack),
    );
  }
  if (
    ts.isPrefixUnaryExpression(node)
    || ts.isPostfixUnaryExpression(node)
    || ts.isAwaitExpression(node)
  ) return evaluateExpression(node.operand || node.expression, locals, effects, stack);
  if (ts.isTemplateExpression(node)) {
    return union(...node.templateSpans.map(
      (span) => evaluateExpression(span.expression, locals, effects, stack),
    ), new Set([UNKNOWN]));
  }
  return new Set([UNKNOWN]);
}

function bindPattern(pattern, values, locals, effects, stack) {
  if (ts.isIdentifier(pattern)) {
    const symbol = symbolAt(pattern);
    if (!symbol) return;
    if (!locals.has(symbol)) locals.set(symbol, new Set());
    merge(locals.get(symbol), values);
    return;
  }
  if (!ts.isObjectBindingPattern(pattern)) {
    if (values.has(PROCESS) || values.has(ENVIRONMENT)) unresolvedDynamicEnv = true;
    return;
  }
  const relevant = values.has(PROCESS) || values.has(ENVIRONMENT);
  for (const element of pattern.elements) {
    if (
      element.dotDotDotToken
      || element.propertyName && ts.isComputedPropertyName(element.propertyName)
    ) {
      if (relevant) unresolvedDynamicEnv = true;
      continue;
    }
    const keyNode = element.propertyName || element.name;
    const key = ts.isIdentifier(keyNode) || ts.isStringLiteral(keyNode)
      ? keyNode.text : null;
    if (key === null) {
      if (relevant) unresolvedDynamicEnv = true;
      continue;
    }
    let childValues = new Set([UNKNOWN]);
    if (values.has(PROCESS) && key === "env") {
      childValues = new Set([ENVIRONMENT]);
      if (values.has(UNKNOWN)) childValues.add(UNKNOWN);
    }
    if (values.has(ENVIRONMENT)) {
      if (effects) addReference(key, element);
      childValues.add(UNKNOWN);
    }
    bindPattern(element.name, childValues, locals, effects, stack);
    if (element.initializer) {
      evaluateExpression(element.initializer, locals, effects, stack);
    }
  }
}

function analyzeNode(node, locals, effects, stack, returns) {
  if (!node) return;
  if (
    ts.isFunctionDeclaration(node)
    || ts.isArrowFunction(node)
    || ts.isFunctionExpression(node)
  ) return;
  if (ts.isVariableDeclaration(node)) {
    if (ts.isIdentifier(node.name)) {
      const symbol = symbolAt(node.name);
      if (symbol) {
        const value = node.initializer
          ? evaluateExpression(node.initializer, locals, effects, stack)
          : new Set();
        if (!locals.has(symbol)) locals.set(symbol, new Set());
        merge(locals.get(symbol), value);
      }
    } else if (node.initializer) {
      const base = evaluateExpression(node.initializer, locals, effects, stack);
      bindPattern(node.name, base, locals, effects, stack);
    }
    return;
  }
  if (ts.isReturnStatement(node)) {
    merge(returns, evaluateExpression(node.expression, locals, effects, stack));
    return;
  }
  if (ts.isExpressionStatement(node)) {
    evaluateExpression(node.expression, locals, effects, stack);
    return;
  }
  if (ts.isThrowStatement(node)) {
    evaluateExpression(node.expression, locals, effects, stack);
    return;
  }
  if (ts.isIfStatement(node)) {
    evaluateExpression(node.expression, locals, effects, stack);
    analyzeNode(node.thenStatement, new Map(locals), effects, stack, returns);
    analyzeNode(node.elseStatement, new Map(locals), effects, stack, returns);
    return;
  }
  ts.forEachChild(node, (child) => analyzeNode(child, locals, effects, stack, returns));
}

function invokeFunction(info, argumentsValues, effects, stack) {
  if (!info) return new Set([UNKNOWN]);
  if (stack.has(info.symbol)) {
    return new Set([UNKNOWN]);
  }
  const nextStack = new Set(stack);
  nextStack.add(info.symbol);
  const locals = new Map();
  info.node.parameters.forEach((parameter, index) => {
    bindPattern(
      parameter.name,
      argumentsValues[index] || new Set([parameterAtom(info, index)]),
      locals,
      effects,
      nextStack,
    );
  });
  const returns = new Set();
  if (ts.isBlock(info.node.body)) {
    for (const statement of info.node.body.statements) {
      analyzeNode(statement, locals, effects, nextStack, returns);
    }
  } else {
    merge(returns, evaluateExpression(info.node.body, locals, effects, nextStack));
  }
  return returns.size > 0 ? returns : new Set([UNKNOWN]);
}

for (let iteration = 0; iteration < assignments.length + 2; iteration += 1) {
  let changed = false;
  for (const assignment of assignments) {
    if (!globalValues.has(assignment.symbol)) globalValues.set(assignment.symbol, new Set());
    changed = merge(
      globalValues.get(assignment.symbol),
      evaluateExpression(assignment.expression, new Map(), false, new Set()),
    ) || changed;
  }
  if (!changed) break;
}

function projectImports(node) {
  if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) {
    const value = node.moduleSpecifier ? stringValue(node.moduleSpecifier) : null;
    if (value && value.startsWith(".")) imports.push(value);
  }
  if (ts.isCallExpression(node)) {
    if (
      node.expression.kind === ts.SyntaxKind.ImportKeyword
      || (ts.isIdentifier(node.expression) && node.expression.text === "require")
    ) {
      if (node.arguments.length !== 1) {
        unresolvedImport = true;
      } else {
        const values = evaluateExpression(node.arguments[0], new Map(), false, new Set());
        const literalValues = [...values]
          .filter((atom) => atom.kind === "literal")
          .map((atom) => atom.value);
        if (values.has(UNKNOWN) || literalValues.length === 0) unresolvedImport = true;
        for (const value of literalValues) {
          if (value.startsWith(".")) imports.push(value);
        }
      }
    }
  }
  ts.forEachChild(node, projectImports);
}

projectImports(sourceFile);
const topLevelReturns = new Set();
const topLevelLocals = new Map();
for (const statement of sourceFile.statements) {
  if (!ts.isFunctionDeclaration(statement)) {
    analyzeNode(statement, topLevelLocals, true, new Set(), topLevelReturns);
  }
}
for (const info of functionInfos.values()) {
  const symbolicArguments = info.parameterSymbols.map(
    (_, index) => new Set([parameterAtom(info, index)]),
  );
  invokeFunction(info, symbolicArguments, true, new Set());
}

process.stdout.write(JSON.stringify({
  imports: [...new Set(imports)].sort(),
  references: references
    .filter((item, index, all) => all.findIndex(
      (candidate) => candidate.reference_name === item.reference_name && candidate.line === item.line,
    ) === index)
    .sort((left, right) => left.reference_name.localeCompare(right.reference_name) || left.line - right.line),
  unresolved_dynamic_env: unresolvedDynamicEnv,
  unresolved_import: unresolvedImport,
}));

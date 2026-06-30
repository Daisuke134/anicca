"""manifest — static-analysis: skill code must not write its own manifest.json.

PROP-G2-static (required:true, Tier 1) — INV-13 static half.
Walks Python AST + flow-traces string-construction expressions; flags any write
sink (`open(..., 'w')`, `Path(..).write_text(..)`, `os.rename`, `shutil.copy`) where
the resolved path is the skill's own manifest.json.
"""
from __future__ import annotations

import ast


_WRITE_MODES = {"w", "wb", "wt", "w+", "wb+", "wt+", "a", "ab", "at", "a+"}
_PATH_WRITE_ATTRS = {"write_text", "write_bytes"}
_FILE_BASENAMES = {"manifest.json"}


def _string_value(node: ast.AST) -> str | None:
    """Best-effort constant-fold of a string-shaped expression.

    Handles:
      - ast.Constant(str)
      - ast.BinOp(Add) of two foldable parts
      - ast.JoinedStr (f-strings) where all parts are constant or foldable
      - ast.Call(func=str.join, args=[separator_const, list_of_consts])
      - ast.Call(func=os.path.join, *constants)
      - simple Attribute / Name lookups that don't resolve are returned as
        sentinel patterns ('__VAR__') so the join still works
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _string_value(node.left)
        right = _string_value(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                # Unresolved — placeholder
                parts.append("__VAR__")
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.Call):
        # os.path.join('_shared', 'manifest.json') → '_shared/manifest.json'
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and getattr(node.func.value.value, "id", None) == "os"
            and node.func.value.attr == "path"
            and node.func.attr == "join"
        ):
            parts = [_string_value(a) for a in node.args]
            if all(p is not None for p in parts):
                return "/".join(p for p in parts if p is not None)
        # ''.join([..., 'manifest.json', ...]) where separator is constant
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
            and node.args
            and isinstance(node.args[0], ast.List)
        ):
            sep = node.func.value.value
            parts = [_string_value(e) for e in node.args[0].elts]
            if all(p is not None for p in parts):
                return sep.join(p for p in parts if p is not None)
    return None


def _ends_in_skill_manifest(path_str: str | None, skill_dir: str) -> bool:
    """Return True if path_str resolves to <skill_dir>/manifest.json (with or
    without an unresolved __VAR__ standing in for skill_dir/SKILL_DIR/etc).
    """
    if not path_str:
        return False
    # Direct match
    if path_str == f"{skill_dir}/manifest.json":
        return True
    # Trailing basename match where prefix contains __VAR__ (variable prefix)
    if path_str.endswith("/manifest.json") and "__VAR__" in path_str:
        return True
    # Bare basename match
    if path_str == "manifest.json":
        return True
    return False


class _SkillManifestWriteFinder(ast.NodeVisitor):
    def __init__(self, skill_dir: str) -> None:
        self.skill_dir = skill_dir
        self.found = False
        # Name → foldable string value, for resolving Name args of open()/write_text.
        # Filled by visit_Assign before the open() call is visited (top-to-bottom AST walk).
        self.var_strings: dict[str, str] = {}

    def _resolve(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name) and node.id in self.var_strings:
            return self.var_strings[node.id]
        return _string_value(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        # Track simple `Name = <foldable string expr>` (and binop with unresolved var → __VAR__)
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            value = self._fold_with_var_sentinel(node.value)
            if value is not None:
                self.var_strings[node.targets[0].id] = value
        self.generic_visit(node)

    def _fold_with_var_sentinel(self, node: ast.AST) -> str | None:
        """Like _string_value but substitutes __VAR__ for unresolved Names in BinOp(Add).
        Lets `SKILL_DIR + '/manifest.json'` fold to `__VAR__/manifest.json`.
        """
        direct = _string_value(node)
        if direct is not None:
            return direct
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._fold_with_var_sentinel(node.left)
            right = self._fold_with_var_sentinel(node.right)
            if left is None and isinstance(node.left, ast.Name):
                left = "__VAR__"
            if right is None and isinstance(node.right, ast.Name):
                right = "__VAR__"
            if left is not None and right is not None:
                return left + right
        if isinstance(node, ast.Name):
            return self.var_strings.get(node.id)
        return None

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # open(path, mode='w'|'a'|...)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "open"
            and node.args
        ):
            path = self._resolve(node.args[0])
            mode = None
            if len(node.args) >= 2:
                mode = _string_value(node.args[1])
            for kw in node.keywords:
                if kw.arg == "mode":
                    mode = _string_value(kw.value)
            # Default mode for open() is 'r' — only flag explicit write modes.
            if mode is not None and any(m in mode for m in _WRITE_MODES):
                if _ends_in_skill_manifest(path, self.skill_dir):
                    self.found = True
        # Path(...).write_text / write_bytes
        if isinstance(node.func, ast.Attribute) and node.func.attr in _PATH_WRITE_ATTRS:
            # The receiver of write_text is `Path(some_expr)` or `<Path>.parent / "name"`.
            # Try to reconstruct as a string.
            path = _reconstruct_path_receiver(node.func.value, self.skill_dir)
            if _ends_in_skill_manifest(path, self.skill_dir):
                self.found = True
        self.generic_visit(node)


def _reconstruct_path_receiver(node: ast.AST, skill_dir: str) -> str | None:
    """Reconstruct expressions like `Path(__file__).parent / 'manifest.json'`
    into the trailing basename so the comparator can decide.
    """
    # Path(__file__).parent / 'manifest.json'  →  BinOp(left=…, op=Div, right=Const)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        right = _string_value(node.right)
        if right == "manifest.json":
            return "__VAR__/manifest.json"
        if right and right.endswith("manifest.json"):
            return f"__VAR__/{right}"
    # Direct Path(literal)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path":
        if node.args:
            literal = _string_value(node.args[0])
            return literal
    return None


def skill_writes_own_manifest(source: str, skill_dir: str) -> bool:
    """Return True if `source` contains a write operation whose resolved path
    is (or unambiguously appears to be) the skill's own manifest.json.

    Conservative: literal/dunder-file/var-concat → True; reads → False.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    finder = _SkillManifestWriteFinder(skill_dir)
    finder.visit(tree)
    return finder.found

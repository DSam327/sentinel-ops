"""
AST Syntax Tree Visitor for SentinelOps.
Performs semantic static analysis on Python source files and Git diffs
to detect N+1 database queries, memory leaks, and timeout regressions.
"""

import ast
import textwrap
from typing import List, Optional, Set
from app.ast_analyzer.rules import (
    ASTViolation,
    ASTViolationType,
    ASTAnalysisReport,
)


class IncidentPatternASTVisitor(ast.NodeVisitor):
    """
    Traverses the Abstract Syntax Tree (AST) of candidate code diffs to uncover
    subtle architectural anti-patterns that static linters miss.
    """

    DB_IO_METHODS = {
        "execute",
        "fetch_one",
        "fetch_all",
        "fetch",
        "query",
        "select",
        "get_one",
        "find",
        "find_one",
        "db_call",
        "commit",
        "flush",
    }

    HTTP_IO_METHODS = {
        "get",
        "post",
        "put",
        "delete",
        "request",
        "send",
    }

    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.violations: List[ASTViolation] = []
        self.loop_stack: List[ast.AST] = []
        self.current_function: Optional[str] = None
        self.current_function_node: Optional[ast.AST] = None
        self.module_dicts: Set[str] = set()

    def _get_snippet(self, node: ast.AST) -> str:
        lineno = getattr(node, "lineno", 1) - 1
        if 0 <= lineno < len(self.source_lines):
            return self.source_lines[lineno].strip()
        return "<source unavailable>"

    def visit_Module(self, node: ast.Module) -> None:
        # First pass: identify module-level dictionaries or caches
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(stmt.value, ast.Dict) or "CACHE" in target.id.upper():
                            self.module_dicts.add(target.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev_fn = self.current_function
        prev_node = self.current_function_node
        self.current_function = node.name
        self.current_function_node = node
        self.generic_visit(node)
        self.current_function = prev_fn
        self.current_function_node = prev_node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        prev_fn = self.current_function
        prev_node = self.current_function_node
        self.current_function = node.name
        self.current_function_node = node
        self.generic_visit(node)
        self.current_function = prev_fn
        self.current_function_node = prev_node

    def visit_For(self, node: ast.For) -> None:
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()

    def visit_While(self, node: ast.While) -> None:
        self.loop_stack.append(node)
        self.generic_visit(node)
        self.loop_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        # Check 1: N+1 Database or Network I/O call inside a loop
        if len(self.loop_stack) > 0:
            method_name = None
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                method_name = node.func.id

            if method_name:
                is_db_call = method_name.lower() in self.DB_IO_METHODS
                is_http_call = False
                if method_name.lower() in self.HTTP_IO_METHODS:
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                        caller_name = node.func.value.id.lower()
                        if any(k in caller_name for k in ("http", "client", "session", "request", "api", "caller")):
                            is_http_call = True
                    elif method_name.lower() in ("request", "send"):
                        is_http_call = True

                if is_db_call or is_http_call:
                    call_type = "Database" if is_db_call else "HTTP"
                    self.violations.append(
                        ASTViolation(
                            violation_type=ASTViolationType.N_PLUS_ONE_IO_IN_LOOP,
                            severity="CRITICAL",
                            line_number=node.lineno,
                            col_offset=node.col_offset,
                            function_context=self.current_function,
                            violating_node=f"Call to {method_name}() inside loop",
                            code_snippet=self._get_snippet(node),
                            explanation=(
                                f"Detected synchronous/sequential {call_type} I/O call (`{method_name}`) "
                                f"inside an iteration loop in function `{self.current_function}`. Under high "
                                f"concurrency, this causes connection pool exhaustion and severe P99 latency degradation."
                            ),
                            remediation_advice=(
                                "Batch the query outside the loop using an `IN (:ids)` clause or a bulk fetch join."
                            ),
                        )
                    )

        # Check 2: Dangerous extended client timeouts
        # e.g., httpx.Timeout(read=60.0) or requests.get(..., timeout=60)
        self._check_timeout_kwargs(node)

        self.generic_visit(node)

    def _check_timeout_kwargs(self, node: ast.Call) -> None:
        for keyword in node.keywords:
            if keyword.arg in ("timeout", "read", "read_timeout"):
                if isinstance(keyword.value, ast.Constant):
                    val = keyword.value.value
                    if isinstance(val, (int, float)) and val > 10.0:
                        self.violations.append(
                            ASTViolation(
                                violation_type=ASTViolationType.DANGEROUS_EXTENDED_TIMEOUT,
                                severity="HIGH",
                                line_number=node.lineno,
                                col_offset=node.col_offset,
                                function_context=self.current_function,
                                violating_node=f"timeout={val}s",
                                code_snippet=self._get_snippet(node),
                                explanation=(
                                    f"Detected client timeout set to {val}s, exceeding standard SLA thresholds (2.0s). "
                                    "When downstream services hang, this causes worker thread starvation and cascading 504 timeouts."
                                ),
                                remediation_advice="Reduce client timeout to <= 2.5s and implement an active circuit breaker.",
                            )
                        )

    def _has_eviction_guard(self, func_node: Optional[ast.AST], dict_name: str) -> bool:
        if not func_node:
            return False
        for subnode in ast.walk(func_node):
            if isinstance(subnode, ast.Call):
                if isinstance(subnode.func, ast.Attribute):
                    if subnode.func.attr in ("popitem", "pop", "clear", "evict", "delete"):
                        return True
            if isinstance(subnode, ast.Compare):
                for comp in [subnode.left] + subnode.comparators:
                    if isinstance(comp, ast.Call) and isinstance(comp.func, ast.Name):
                        if comp.func.id == "len":
                            return True
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        # Check 3: Unbounded in-memory dictionary caching
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                if isinstance(target.value, ast.Name):
                    dict_name = target.value.id
                    if dict_name in self.module_dicts or "CACHE" in dict_name.upper():
                        # Only flag if no eviction mechanism or capacity guard exists
                        if not self._has_eviction_guard(self.current_function_node, dict_name):
                            self.violations.append(
                                ASTViolation(
                                    violation_type=ASTViolationType.UNBOUNDED_IN_MEMORY_CACHE,
                                    severity="CRITICAL",
                                    line_number=node.lineno,
                                    col_offset=node.col_offset,
                                    function_context=self.current_function,
                                    violating_node=f"Subscript assignment to {dict_name}",
                                    code_snippet=self._get_snippet(node),
                                    explanation=(
                                        f"Detected mutating assignment to module-level cache `{dict_name}` inside "
                                        f"function `{self.current_function}` without an eviction policy, max size guard, or TTL. "
                                        "This leads to progressive heap fragmentation and OOMKilled pod crashes (Exit 137)."
                                    ),
                                    remediation_advice="Replace with a bounded LRU cache (e.g., `cachetools.TTLCache(maxsize=1000, ttl=300)`).",
                                )
                            )
        self.generic_visit(node)


class CodeASTAnalyzer:
    """Entry point for AST code analysis."""

    @staticmethod
    def analyze_source_code(source_code: str, filename: Optional[str] = None) -> ASTAnalysisReport:
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return ASTAnalysisReport(
                source_file=filename,
                has_critical_violations=True,
                violations=[
                    ASTViolation(
                        violation_type=ASTViolationType.SYNTAX_ERROR,
                        severity="CRITICAL",
                        line_number=e.lineno or 1,
                        col_offset=e.offset or 0,
                        function_context=None,
                        violating_node="SyntaxError",
                        code_snippet=e.text or "",
                        explanation=f"Source code has invalid Python syntax: {e.msg}",
                        remediation_advice="Fix syntax error before running.",
                    )
                ],
                analyzed_lines_count=len(source_code.splitlines()),
            )

        lines = source_code.splitlines()
        visitor = IncidentPatternASTVisitor(source_lines=lines)
        visitor.visit(tree)

        has_critical = any(v.severity in ("CRITICAL", "HIGH") for v in visitor.violations)
        return ASTAnalysisReport(
            source_file=filename,
            has_critical_violations=has_critical,
            violations=visitor.violations,
            analyzed_lines_count=len(lines),
        )

    @classmethod
    def analyze_diff(cls, diff_str: str, filename: Optional[str] = None) -> ASTAnalysisReport:
        """
        Extracts resulting Python statements (context ' ' and added '+') from a unified diff
        and performs AST analysis. Skips non-Python files (.json, .sql, etc.).
        """
        # 1. Check target file extension
        target_is_python = False
        for line in diff_str.splitlines():
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                if line.endswith(".py"):
                    target_is_python = True
                    break

        if not target_is_python and filename and not filename.endswith(".py"):
            return ASTAnalysisReport(
                source_file=filename,
                has_critical_violations=False,
                violations=[],
                analyzed_lines_count=len(diff_str.splitlines()),
            )

        # 2. Extract resulting lines (context ' ' and added '+')
        resulting_lines = []
        for line in diff_str.splitlines():
            if (line.startswith("+") or line.startswith(" ")) and not line.startswith("+++"):
                resulting_lines.append(line[1:])

        raw_code = "\n".join(resulting_lines)
        dedented = textwrap.dedent(raw_code).strip()
        if not dedented:
            return ASTAnalysisReport(
                source_file=filename,
                has_critical_violations=False,
                violations=[],
                analyzed_lines_count=0,
            )

        # 3. Attempt parse directly, then fallback to wrapping if function fragment
        try:
            tree = ast.parse(dedented)
            code_to_analyze = dedented
        except SyntaxError:
            if "await " in dedented:
                code_to_analyze = f"async def _diff_scope():\n{textwrap.indent(dedented, '    ')}"
            else:
                code_to_analyze = f"def _diff_scope():\n{textwrap.indent(dedented, '    ')}"
            try:
                tree = ast.parse(code_to_analyze)
            except SyntaxError:
                return ASTAnalysisReport(
                    source_file=filename,
                    has_critical_violations=False,
                    violations=[],
                    analyzed_lines_count=len(resulting_lines),
                )

        lines = code_to_analyze.splitlines()
        visitor = IncidentPatternASTVisitor(source_lines=lines)
        visitor.visit(tree)

        has_critical = any(v.severity in ("CRITICAL", "HIGH") for v in visitor.violations)
        return ASTAnalysisReport(
            source_file=filename,
            has_critical_violations=has_critical,
            violations=visitor.violations,
            analyzed_lines_count=len(lines),
        )


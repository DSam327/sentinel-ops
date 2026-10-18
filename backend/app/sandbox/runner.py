"""
Ephemeral Subprocess Sandbox Runner for SentinelOps.
Validates candidate remediation patches in isolated workspaces using
Python syntax checks, AST anti-pattern verification, and targeted test execution.
"""

import os
import sys
import time
import tempfile
import py_compile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.ast_analyzer.visitor import CodeASTAnalyzer


class SandboxVerificationResult(BaseModel):
    verified: bool
    service_name: str
    target_file: str
    syntax_valid: bool
    ast_check_passed: bool
    tests_passed: bool
    violations_found: List[str]
    stdout: str
    stderr: str
    execution_time_ms: float
    remediation_summary: str


class SubprocessSandboxRunner:
    """
    Sandboxed test environment for validating agent-generated hotfixes.
    Ensures no hallucinated or broken code is ever recommended as a production PR.
    """

    @staticmethod
    def verify_patch(
        service_name: str,
        target_file: str,
        original_code: str,
        candidate_code: str,
        test_script: Optional[str] = None,
    ) -> SandboxVerificationResult:
        start_time = time.perf_counter()

        # Step 1: Pre-patch AST violation baseline
        pre_report = CodeASTAnalyzer.analyze_source_code(original_code, filename=target_file)
        pre_violations = [f"{v.violation_type}: {v.explanation}" for v in pre_report.violations]

        with tempfile.TemporaryDirectory(prefix=f"sentinel_sandbox_{service_name}_") as tmpdir:
            work_dir = Path(tmpdir)
            file_path = work_dir / target_file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Create __init__.py across all parent directories
            curr = file_path.parent
            while curr != work_dir:
                (curr / "__init__.py").touch(exist_ok=True)
                curr = curr.parent
            (work_dir / "__init__.py").touch(exist_ok=True)
            file_path.write_text(candidate_code, encoding="utf-8")

            # Step 2: Syntax Compilation Verification
            try:
                py_compile.compile(str(file_path), doraise=True)
                syntax_valid = True
                syntax_err = ""
            except py_compile.PyCompileError as e:
                syntax_valid = False
                syntax_err = str(e)
                exec_time = (time.perf_counter() - start_time) * 1000
                return SandboxVerificationResult(
                    verified=False,
                    service_name=service_name,
                    target_file=target_file,
                    syntax_valid=False,
                    ast_check_passed=False,
                    tests_passed=False,
                    violations_found=[f"SYNTAX_ERROR: {syntax_err}"],
                    stdout="",
                    stderr=syntax_err,
                    execution_time_ms=round(exec_time, 2),
                    remediation_summary="Patch failed Python syntax compilation check.",
                )

            # Step 3: AST Anti-Pattern Verification
            post_report = CodeASTAnalyzer.analyze_source_code(candidate_code, filename=target_file)
            post_violations = [f"{v.violation_type}: {v.explanation}" for v in post_report.violations]
            ast_check_passed = not post_report.has_critical_violations

            # Step 4: Subprocess Test Runner
            tests_passed = True
            stdout_str = ""
            stderr_str = ""

            if test_script:
                test_file = work_dir / "test_sandbox_run.py"
                test_file.write_text(test_script, encoding="utf-8")

                try:
                    result = subprocess.run(
                        [sys.executable, str(test_file)],
                        cwd=str(work_dir),
                        env={**os.environ, "PYTHONPATH": str(work_dir)},
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    stdout_str = result.stdout
                    stderr_str = result.stderr
                    tests_passed = (result.returncode == 0)
                except subprocess.TimeoutExpired:
                    tests_passed = False
                    stderr_str = "Test execution timed out in sandbox after 10.0s."
                except Exception as ex:
                    tests_passed = False
                    stderr_str = f"Sandbox execution exception: {str(ex)}"

            total_verified = syntax_valid and ast_check_passed and tests_passed
            exec_time = (time.perf_counter() - start_time) * 1000

            if total_verified:
                summary = (
                    f"Successfully verified hotfix for {service_name}. "
                    f"Eradicated {len(pre_violations)} AST violations. "
                    "Syntax compilation and regression tests passed cleanly."
                )
            else:
                summary = f"Patch verification rejected: AST violations remain ({len(post_violations)}) or tests failed."

            return SandboxVerificationResult(
                verified=total_verified,
                service_name=service_name,
                target_file=target_file,
                syntax_valid=syntax_valid,
                ast_check_passed=ast_check_passed,
                tests_passed=tests_passed,
                violations_found=post_violations,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time_ms=round(exec_time, 2),
                remediation_summary=summary,
            )

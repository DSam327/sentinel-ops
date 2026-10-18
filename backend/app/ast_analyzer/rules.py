"""
Rule definitions and AST Match schema for SentinelOps static code analyzer.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ASTViolationType(str, Enum):
    N_PLUS_ONE_IO_IN_LOOP = "N_PLUS_ONE_IO_IN_LOOP"
    UNBOUNDED_IN_MEMORY_CACHE = "UNBOUNDED_IN_MEMORY_CACHE"
    DANGEROUS_EXTENDED_TIMEOUT = "DANGEROUS_EXTENDED_TIMEOUT"
    MISSING_CIRCUIT_BREAKER = "MISSING_CIRCUIT_BREAKER"
    SYNTAX_ERROR = "SYNTAX_ERROR"


class ASTViolation(BaseModel):
    violation_type: ASTViolationType
    severity: str  # CRITICAL, HIGH, MEDIUM
    line_number: int
    col_offset: int
    function_context: Optional[str] = None
    violating_node: str
    code_snippet: str
    explanation: str
    remediation_advice: str


class ASTAnalysisReport(BaseModel):
    source_file: Optional[str] = None
    has_critical_violations: bool
    violations: List[ASTViolation]
    analyzed_lines_count: int

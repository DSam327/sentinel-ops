"""
Unit tests for AST Syntax Analyzer (visitor and rules).
"""

from app.ast_analyzer.visitor import CodeASTAnalyzer
from app.ast_analyzer.rules import ASTViolationType


def test_detects_n_plus_one_in_loop():
    bad_code = """
def charge_users(users):
    for u in users:
        # DB call inside loop
        res = db.fetch_one(f"SELECT * FROM balance WHERE uid = '{u}'")
    return True
"""
    report = CodeASTAnalyzer.analyze_source_code(bad_code, filename="payment.py")
    assert report.has_critical_violations is True
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.violation_type == ASTViolationType.N_PLUS_ONE_IO_IN_LOOP
    assert v.line_number == 5
    assert "db.fetch_one" in v.code_snippet


def test_clean_batched_query_passes_ast_check():
    clean_code = """
def charge_users_batched(users):
    user_ids = [u.id for u in users]
    # Single batched query outside loop
    records = db.fetch_all("SELECT * FROM balance WHERE uid IN (:ids)", {"ids": user_ids})
    return records
"""
    report = CodeASTAnalyzer.analyze_source_code(clean_code, filename="payment_clean.py")
    assert report.has_critical_violations is False
    assert len(report.violations) == 0


def test_detects_unbounded_cache_leak():
    leaky_code = """
_GLOBAL_SKU_CACHE = {}

def get_sku(sku_id, data):
    _GLOBAL_SKU_CACHE[sku_id] = data
    return _GLOBAL_SKU_CACHE[sku_id]
"""
    report = CodeASTAnalyzer.analyze_source_code(leaky_code, filename="sku.py")
    assert report.has_critical_violations is True
    assert any(v.violation_type == ASTViolationType.UNBOUNDED_IN_MEMORY_CACHE for v in report.violations)


def test_detects_dangerous_timeout():
    risky_timeout_code = """
import httpx

def call_partner():
    client = httpx.Client(timeout=60.0)
    return client.get("https://partner.api/ship")
"""
    report = CodeASTAnalyzer.analyze_source_code(risky_timeout_code, filename="shipping.py")
    assert any(v.violation_type == ASTViolationType.DANGEROUS_EXTENDED_TIMEOUT for v in report.violations)

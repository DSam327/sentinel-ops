"""
Unit tests for SubprocessSandboxRunner validating ephemeral patch verification.
"""

from app.sandbox.runner import SubprocessSandboxRunner


def test_sandbox_rejects_syntax_error():
    bad_syntax = "def broken_func(: invalid syntax here"
    result = SubprocessSandboxRunner.verify_patch(
        service_name="payment-service",
        target_file="app/broken.py",
        original_code="def old(): pass",
        candidate_code=bad_syntax,
    )
    assert result.verified is False
    assert result.syntax_valid is False
    assert "SYNTAX_ERROR" in result.violations_found[0]


def test_sandbox_rejects_patch_retaining_n_plus_one():
    still_has_n1 = """
def charge_all(users):
    for u in users:
        db.fetch_one(f"SELECT * FROM accounts WHERE id = '{u}'")
    return True
"""
    result = SubprocessSandboxRunner.verify_patch(
        service_name="payment-service",
        target_file="app/charge.py",
        original_code="def old(): pass",
        candidate_code=still_has_n1,
    )
    assert result.verified is False
    assert result.syntax_valid is True
    assert result.ast_check_passed is False
    assert any("N_PLUS_ONE" in v for v in result.violations_found)


def test_sandbox_approves_clean_patch_with_passing_test():
    clean_code = """
def batch_charge(user_ids):
    if not user_ids:
        return []
    # Batched call without loop
    return [{"id": uid, "status": "CONFIRMED"} for uid in user_ids]
"""
    test_script = """
from app.charge import batch_charge
assert batch_charge(["u1", "u2"]) == [
    {"id": "u1", "status": "CONFIRMED"},
    {"id": "u2", "status": "CONFIRMED"}
]
print("ALL TESTS PASSED")
"""
    result = SubprocessSandboxRunner.verify_patch(
        service_name="payment-service",
        target_file="app/charge.py",
        original_code="def old(): for u in users: db.fetch_one()",
        candidate_code=clean_code,
        test_script=test_script,
    )
    assert result.verified is True
    assert result.syntax_valid is True
    assert result.ast_check_passed is True
    assert result.tests_passed is True
    assert "ALL TESTS PASSED" in result.stdout

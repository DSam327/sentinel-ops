"""
Git repository simulator for SentinelOps.
Provides commit histories, blame annotations, and unified AST diffs.
"""

from typing import List, Optional, Dict
from app.core.models import GitCommit


class GitTracker:
    """
    Simulates Git version control across the microservice repositories.
    Allows searching commits by service, timeframe, and inspecting diffs.
    """

    def __init__(self):
        self._commits: Dict[str, GitCommit] = {}
        self._initialize_commits()

    def _initialize_commits(self) -> None:
        commits_data = [
            # Offending commit for Scenario 1: N_PLUS_ONE_QUERY
            GitCommit(
                commit_hash="f4a81c79",
                author="alex.chen@company.internal",
                timestamp_mins_ago=25,
                service_name="payment-service",
                message="feat(payment): eager validate user payment methods during checkout",
                files_changed=["app/services/payment_orchestrator.py"],
                risk_score=0.92,
                diff="""--- a/app/services/payment_orchestrator.py
+++ b/app/services/payment_orchestrator.py
@@ -42,7 +42,12 @@ class PaymentOrchestrator:
     async def verify_and_charge(self, user_id: str, amount_cents: int) -> ChargeResult:
-        # Old batch query: single index lookup
-        # verified_cards = await self.db.fetch_all("SELECT * FROM cards WHERE user_id = :uid AND is_active = true", {"uid": user_id})
+        # New eager verification: iterates over all user cards sequentially
+        user_cards = await self.db.fetch_all("SELECT id FROM cards WHERE user_id = :uid", {"uid": user_id})
+        verified_cards = []
+        for card in user_cards:
+            # REGRESSION: N+1 unindexed query inside loop without connection release
+            status = await self.db.fetch_one(f"SELECT * FROM card_verification WHERE card_id = '{card['id']}'")
+            if status and status.get("is_valid"):
+                verified_cards.append(card)
         if not verified_cards:
             raise PaymentError("No valid payment method found")
""",
            ),
            # Offending commit for Scenario 2: CASCADING_TIMEOUT
            GitCommit(
                commit_hash="b92d04a1",
                author="sarah.ops@company.internal",
                timestamp_mins_ago=35,
                service_name="order-service",
                message="fix(order): bump shipping partner timeout to 60s for bulk shipments",
                files_changed=["app/clients/shipping_client.py"],
                risk_score=0.88,
                diff="""--- a/app/clients/shipping_client.py
+++ b/app/clients/shipping_client.py
@@ -14,6 +14,8 @@ class ShippingClient:
     def __init__(self, endpoint: str):
         self.endpoint = endpoint
-        # Safe default SLA timeout with circuit breaker
-        self.timeout = httpx.Timeout(connect=0.5, read=2.0, write=1.0)
+        # REGRESSION: Increased read timeout to 60s without thread pool isolation
+        # Causes request queue starvation when third-party provider degrades
+        self.timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0)
+        self.max_retries = 3
""",
            ),
            # Offending commit for Scenario 3: MEMORY_LEAK
            GitCommit(
                commit_hash="c319e73b",
                author="david.swe@company.internal",
                timestamp_mins_ago=48,
                service_name="inventory-service",
                message="perf(inventory): add in-memory memoization cache for SKU lookups",
                files_changed=["app/services/sku_cache.py"],
                risk_score=0.95,
                diff="""--- a/app/services/sku_cache.py
+++ b/app/services/sku_cache.py
@@ -8,3 +8,11 @@ import copy
 
+# REGRESSION: Unbounded dictionary with deepcopy and zero TTL/LRU eviction
+_IN_MEMORY_SKU_CACHE = {}
+
 def get_cached_sku_payload(sku_id: str, raw_db_row: dict) -> dict:
+    if sku_id not in _IN_MEMORY_SKU_CACHE:
+        # Storing uncompressed raw JSON payload in process heap indefinitely
+        _IN_MEMORY_SKU_CACHE[sku_id] = copy.deepcopy(raw_db_row)
+    return _IN_MEMORY_SKU_CACHE[sku_id]
""",
            ),
            # Offending commit for Scenario 4: REDIS_STAMPEDE
            GitCommit(
                commit_hash="e742ab15",
                author="mike.lead@company.internal",
                timestamp_mins_ago=40,
                service_name="order-service",
                message="chore(cache): harmonize redis cache TTL across all category catalogs",
                files_changed=["app/cache/catalog_cache.py"],
                risk_score=0.85,
                diff="""--- a/app/cache/catalog_cache.py
+++ b/app/cache/catalog_cache.py
@@ -21,5 +21,4 @@ class CatalogCacheManager:
     def get_category_cache_ttl(self) -> int:
-        # Previously had 10-minute jitter to prevent cache stampede
-        # return 3600 + random.randint(0, 600)
+        # REGRESSION: Deterministic TTL without jitter causes simultaneous thundering herd
+        return 3600
""",
            ),
            # Benign baseline commits (noise for agent to distinguish)
            GitCommit(
                commit_hash="88a101ee",
                author="emily.ui@company.internal",
                timestamp_mins_ago=60,
                service_name="api-gateway",
                message="chore(headers): update cors allowed origins for staging",
                files_changed=["config/cors.json"],
                risk_score=0.05,
                diff="""--- a/config/cors.json
+++ b/config/cors.json
@@ -3,2 +3,3 @@
   "https://admin.staging.internal",
+  "https://preview.internal"
""",
            ),
            GitCommit(
                commit_hash="41cb9820",
                author="alex.chen@company.internal",
                timestamp_mins_ago=75,
                service_name="auth-service",
                message="refactor(jwt): add aud claim validation check",
                files_changed=["app/token/validator.py"],
                risk_score=0.15,
                diff="""--- a/app/token/validator.py
+++ b/app/token/validator.py
@@ -19,2 +19,4 @@ def validate_jwt(token: str) -> dict:
     claims = jwt.decode(token, algorithms=["RS256"])
+    if "aud" not in claims:
+        raise InvalidTokenError("Missing aud claim")
""",
            ),
            GitCommit(
                commit_hash="11f208aa",
                author="jessica.db@company.internal",
                timestamp_mins_ago=120,
                service_name="postgres-primary",
                message="db(migration): add read replica connection pool warmup",
                files_changed=["db/migrations/20260401_warmup.sql"],
                risk_score=0.10,
                diff="""--- a/db/migrations/20260401_warmup.sql
+++ b/db/migrations/20260401_warmup.sql
@@ -1,1 +1,2 @@
+-- Warmup connection query
+SELECT 1;
""",
            ),
        ]

        for c in commits_data:
            self._commits[c.commit_hash] = c

    def get_recent_commits(
        self, service_name: Optional[str] = None, max_age_mins: int = 180
    ) -> List[GitCommit]:
        """Returns commits ordered by timestamp_mins_ago ascending (most recent first)."""
        results = [
            c
            for c in self._commits.values()
            if (service_name is None or c.service_name == service_name)
            and c.timestamp_mins_ago <= max_age_mins
        ]
        return sorted(results, key=lambda x: x.timestamp_mins_ago)

    def get_commit_by_hash(self, commit_hash: str) -> Optional[GitCommit]:
        return self._commits.get(commit_hash)

    def search_commits_by_keyword(self, keyword: str) -> List[GitCommit]:
        keyword_lower = keyword.lower()
        matches = []
        for c in self._commits.values():
            if (
                keyword_lower in c.message.lower()
                or keyword_lower in c.diff.lower()
                or any(keyword_lower in f.lower() for f in c.files_changed)
            ):
                matches.append(c)
        return matches

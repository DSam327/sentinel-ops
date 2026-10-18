import React, { useState } from 'react';
import { Cpu, Play, AlertTriangle, CheckCircle, Code, ShieldAlert } from 'lucide-react';

const SAMPLE_PRESETS: { [key: string]: { title: string; code: string } } = {
  n_plus_one: {
    title: 'N+1 Query Antipattern',
    code: `async def process_user_cards(user_ids, db_pool):\n    results = []\n    for uid in user_ids:\n        # AST flags this execute inside a for/while loop\n        card = await db_pool.fetch("SELECT * FROM cards WHERE user_id = $1", uid)\n        results.append(card)\n    return results\n`,
  },
  memory_leak: {
    title: 'Unbounded Cache Leak',
    code: `GLOBAL_SKU_CACHE = {}\n\ndef lookup_sku_specs(sku_id, raw_metadata):\n    # AST flags assignment to module-level cache without eviction/size guard\n    GLOBAL_SKU_CACHE[sku_id] = raw_metadata\n    return GLOBAL_SKU_CACHE[sku_id]\n`,
  },
  dangerous_timeout: {
    title: 'Excessive / Blocking Timeout',
    code: `import httpx\n\nasync def call_shipping_service(order_id):\n    # AST flags timeout >= 30.0s starving event loop / thread pool\n    client = httpx.AsyncClient(timeout=60.0)\n    resp = await client.get(f"https://shipping.internal/orders/{order_id}")\n    return resp.json()\n`,
  },
  clean_batched: {
    title: 'Optimized Batch Query (Clean)',
    code: `async def process_user_cards(user_ids, db_pool):\n    # AST approves batched single query with WHERE id = ANY($1)\n    return await db_pool.fetch("SELECT * FROM cards WHERE user_id = ANY($1)", user_ids)\n`,
  },
};

export const ASTPlaygroundModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const [code, setCode] = useState(SAMPLE_PRESETS.n_plus_one.code);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  if (!isOpen) return null;

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      const res = await fetch('/api/ast/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code_or_diff: code, filename: 'custom_inspect.py' }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
      }
    } catch (err) {
      console.error('AST inspect error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: '24px',
      }}
    >
      <div
        style={{
          background: '#0d1527',
          border: '1px solid #1e293b',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '950px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#090d16',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                background: 'rgba(139, 92, 246, 0.1)',
                padding: '8px',
                borderRadius: '8px',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}
            >
              <Cpu style={{ width: '20px', height: '20px', color: '#a855f7' }} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>
                Interactive Python AST Static Analyzer Playground
              </h2>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                Paste arbitrary Python code or diffs to test syntax tree visitor rules in real time
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '4px 8px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Presets Bar */}
        <div
          style={{
            padding: '12px 24px',
            background: '#0d1527',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
            Presets:
          </span>
          {Object.entries(SAMPLE_PRESETS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => {
                setCode(preset.code);
                setResult(null);
              }}
              style={{
                background: '#1e293b',
                color: '#e2e8f0',
                border: '1px solid #334155',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {preset.title}
            </button>
          ))}
        </div>

        {/* Body Split */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', flex: 1, overflow: 'hidden' }}>
          {/* Editor Left */}
          <div style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid #1e293b', background: '#090d16' }}>
            <div style={{ padding: '8px 16px', background: '#090d16', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontFamily: 'monospace', color: '#64748b' }}>
                Python Source / Unified Diff Input
              </span>
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'linear-gradient(135deg, #9333ea, #7c3aed)',
                  color: 'white',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: isAnalyzing ? 'not-allowed' : 'pointer',
                }}
              >
                <Play style={{ width: '13px', height: '13px' }} />
                {isAnalyzing ? 'Visiting AST...' : 'Analyze Syntax Tree'}
              </button>
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste arbitrary Python snippet here..."
              style={{
                flex: 1,
                width: '100%',
                padding: '16px',
                background: '#090d16',
                color: '#38bdf8',
                border: 'none',
                outline: 'none',
                fontFamily: 'Consolas, Monaco, monospace',
                fontSize: '13px',
                lineHeight: '1.5',
                resize: 'none',
              }}
            />
          </div>

          {/* Results Right */}
          <div style={{ padding: '20px', overflowY: 'auto', background: '#0d1527', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Code style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
              AST Static Analysis Verdict
            </div>

            {!result && (
              <div style={{ color: '#64748b', fontSize: '12px', fontStyle: 'italic', padding: '24px 0', textAlign: 'center' }}>
                Click &quot;Analyze Syntax Tree&quot; to execute NodeVisitor rules against the code snippet.
              </div>
            )}

            {result && (
              <>
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: result.has_errors
                      ? 'rgba(244, 63, 94, 0.1)'
                      : result.has_antipatterns
                      ? 'rgba(245, 158, 11, 0.1)'
                      : 'rgba(16, 185, 129, 0.1)',
                    border: `1px solid ${
                      result.has_errors
                        ? '#f43f5e'
                        : result.has_antipatterns
                        ? '#f59e0b'
                        : '#10b981'
                    }`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  {result.has_errors ? (
                    <ShieldAlert style={{ width: '20px', height: '20px', color: '#f43f5e' }} />
                  ) : result.has_antipatterns ? (
                    <AlertTriangle style={{ width: '20px', height: '20px', color: '#f59e0b' }} />
                  ) : (
                    <CheckCircle style={{ width: '20px', height: '20px', color: '#10b981' }} />
                  )}
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                      {result.has_errors
                        ? 'Syntax Compilation Error'
                        : result.has_antipatterns
                        ? `Antipattern Detected (${result.antipatterns.length} violation)`
                        : 'Clean Code: No Architectural Antipatterns'}
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                      Confidence: {result.confidence_score * 100}% • AST Nodes Inspected
                    </div>
                  </div>
                </div>

                {result.antipatterns.map((ap: any, i: number) => (
                  <div
                    key={i}
                    style={{
                      background: '#090d16',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#f43f5e' }}>
                        {ap.pattern_type}
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          background: 'rgba(244, 63, 94, 0.15)',
                          color: '#f43f5e',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontWeight: 700,
                        }}
                      >
                        {ap.severity}
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#cbd5e1' }}>{ap.description}</div>
                    <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace' }}>
                      Line {ap.line_number}: <span style={{ color: '#f8fafc' }}>{ap.code_snippet}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '6px 8px', borderRadius: '4px', marginTop: '4px' }}>
                      <strong>Remediation:</strong> {ap.suggested_fix}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

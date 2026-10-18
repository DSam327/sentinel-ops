import React, { useState } from 'react';
import { Play, Award, CheckCircle2, XCircle, Clock, Zap, BarChart3 } from 'lucide-react';

interface BenchmarkScenarioResult {
  scenario_id: string;
  scenario_title: string;
  expected_root_cause_service: string;
  identified_root_cause_service: string;
  root_cause_accurate: boolean;
  expected_commit_hash: string;
  identified_commit_hash: string;
  commit_accurate: boolean;
  sandbox_verified: boolean;
  iterations_count: number;
  elapsed_time_ms: number;
}

interface BenchmarkSuiteReport {
  total_scenarios_tested: number;
  root_cause_accuracy_pct: number;
  commit_isolation_accuracy_pct: number;
  sandbox_verification_pass_rate_pct: number;
  avg_convergence_steps: number;
  avg_resolution_time_ms: number;
  scenario_results: BenchmarkScenarioResult[];
}

export const BenchmarkModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [report, setReport] = useState<BenchmarkSuiteReport | null>(null);

  if (!isOpen) return null;

  const handleRunBenchmark = async () => {
    setIsRunning(true);
    try {
      const res = await fetch('/api/benchmark/run', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (err) {
      console.error('Benchmark execution error:', err);
    } finally {
      setIsRunning(false);
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
          maxWidth: '850px',
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
            padding: '20px 24px',
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
                background: 'rgba(56, 189, 248, 0.1)',
                padding: '8px',
                borderRadius: '8px',
                border: '1px solid rgba(56, 189, 248, 0.2)',
              }}
            >
              <BarChart3 style={{ width: '20px', height: '20px', color: '#38bdf8' }} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>
                Quantitative SRE Benchmark Suite (Evals)
              </h2>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                Empirical recall & accuracy testing across temporal microservice failure modes
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

        {/* Content Body */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Top Action Box */}
          <div
            style={{
              background: '#090d16',
              border: '1px solid #1e293b',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc' }}>
                Automated Harness: 3 Failure Modes (Recall@1, Sandbox Pass, Step Budget)
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                Executes multi-agent swarm against isolated synthetic trace trees and measures convergence.
              </div>
            </div>
            <button
              onClick={handleRunBenchmark}
              disabled={isRunning}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                background: isRunning ? '#334155' : 'linear-gradient(135deg, #0284c7, #2563eb)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: isRunning ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              {isRunning ? (
                <>
                  <Clock style={{ width: '16px', height: '16px', animation: 'spin 1s linear infinite' }} />
                  Evaluating Swarm...
                </>
              ) : (
                <>
                  <Play style={{ width: '16px', height: '16px' }} />
                  Execute Full Benchmark
                </>
              )}
            </button>
          </div>

          {/* Metric KPI Cards */}
          {report && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                <div style={{ background: '#090d16', border: '1px solid #1e293b', padding: '14px', borderRadius: '10px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                    Recall@1 (Root Cause)
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: '#10b981', marginTop: '4px' }}>
                    {report.root_cause_accuracy_pct}%
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                    {report.total_scenarios_tested} / {report.total_scenarios_tested} isolated
                  </div>
                </div>

                <div style={{ background: '#090d16', border: '1px solid #1e293b', padding: '14px', borderRadius: '10px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                    Commit Isolation
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>
                    {report.commit_isolation_accuracy_pct}%
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                    AST git blame match
                  </div>
                </div>

                <div style={{ background: '#090d16', border: '1px solid #1e293b', padding: '14px', borderRadius: '10px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                    Sandbox Hotfix Rate
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: '#a855f7', marginTop: '4px' }}>
                    {report.sandbox_verification_pass_rate_pct}%
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                    Zero syntax or test regression
                  </div>
                </div>

                <div style={{ background: '#090d16', border: '1px solid #1e293b', padding: '14px', borderRadius: '10px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                    Avg Resolution Time
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: '#f59e0b', marginTop: '4px' }}>
                    {report.avg_resolution_time_ms} ms
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                    Avg {report.avg_convergence_steps} reasoning steps
                  </div>
                </div>
              </div>

              {/* Breakdown Table */}
              <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: '12px', overflow: 'hidden' }}>
                <div style={{ padding: '12px 16px', borderBottom: '1px solid #1e293b', fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
                  Scenario-Level Breakdown
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: '#0d1527', color: '#64748b', borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '10px 16px' }}>Scenario</th>
                      <th style={{ padding: '10px 16px' }}>Expected Service</th>
                      <th style={{ padding: '10px 16px' }}>Identified Service</th>
                      <th style={{ padding: '10px 16px' }}>Commit Hash</th>
                      <th style={{ padding: '10px 16px' }}>Sandbox</th>
                      <th style={{ padding: '10px 16px' }}>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.scenario_results.map((r) => (
                      <tr key={r.scenario_id} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc' }}>
                          {r.scenario_title}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#94a3b8' }}>
                          {r.expected_root_cause_service}
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              color: r.root_cause_accurate ? '#10b981' : '#f43f5e',
                            }}
                          >
                            {r.root_cause_accurate ? <CheckCircle2 style={{ width: '14px', height: '14px' }} /> : <XCircle style={{ width: '14px', height: '14px' }} />}
                            {r.identified_root_cause_service}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#38bdf8' }}>
                          {r.identified_commit_hash}
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span
                            style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 600,
                              background: r.sandbox_verified ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                              color: r.sandbox_verified ? '#10b981' : '#f43f5e',
                            }}
                          >
                            {r.sandbox_verified ? 'PASSED' : 'FAILED'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', color: '#94a3b8', fontFamily: 'monospace' }}>
                          {r.elapsed_time_ms} ms
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

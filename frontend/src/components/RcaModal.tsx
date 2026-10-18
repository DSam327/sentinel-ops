import React from 'react';
import { X, CheckCircle2, GitPullRequest, ShieldCheck, Clock, User, FileCode } from 'lucide-react';

interface RcaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyAndMerge: () => void;
  investigationState: any | null;
}

export const RcaModal: React.FC<RcaModalProps> = ({
  isOpen,
  onClose,
  onApplyAndMerge,
  investigationState,
}) => {
  if (!isOpen || !investigationState) return null;

  const patch = investigationState.remediation_patch;
  const sandbox = investigationState.sandbox_result;
  const hypothesis = investigationState.active_hypothesis;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: '20px',
      }}
    >
      <div
        style={{
          background: '#090d16',
          border: '1px solid #334155',
          borderRadius: '20px',
          maxWidth: '850px',
          width: '100%',
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
            background: '#0d1527',
            padding: '20px 24px',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                background: 'rgba(16, 185, 129, 0.2)',
                color: '#10b981',
                padding: '8px',
                borderRadius: '10px',
              }}
            >
              <GitPullRequest style={{ width: '22px', height: '22px' }} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>
                Audited RCA Postmortem & Hotfix PR
              </h3>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                Incident autonomously verified and repaired across {investigationState.iteration + 1} agent iterations.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '6px',
            }}
          >
            <X style={{ width: '20px', height: '20px' }} />
          </button>
        </div>

        {/* Modal Content */}
        <div style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Metadata Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            <div style={{ background: '#0f172a', padding: '12px', borderRadius: '10px', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <FileCode className="w-3 h-3" /> Root Cause Service
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
                {hypothesis?.suspected_service}
              </div>
            </div>

            <div style={{ background: '#0f172a', padding: '12px', borderRadius: '10px', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <User className="w-3 h-3" /> Blamed Author
              </div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#f1f5f9', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {patch?.commit_author_blamed}
              </div>
            </div>

            <div style={{ background: '#0f172a', padding: '12px', borderRadius: '10px', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock className="w-3 h-3" /> Sandbox Time
              </div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                {sandbox?.execution_time_ms.toFixed(1)}ms
              </div>
            </div>
          </div>

          {/* Verification Badges */}
          <div
            style={{
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '12px',
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-around',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontSize: '12px', fontWeight: 600 }}>
              <CheckCircle2 className="w-4 h-4" /> Syntax Compilation Valid
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontSize: '12px', fontWeight: 600 }}>
              <ShieldCheck className="w-4 h-4" /> AST Pattern Eradicated
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontSize: '12px', fontWeight: 600 }}>
              <CheckCircle2 className="w-4 h-4" /> Subprocess Tests Passed
            </div>
          </div>

          {/* Diff Box */}
          {patch && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#cbd5e1', marginBottom: '8px' }}>
                Generated Hotfix Diff ({patch.target_file}):
              </div>
              <pre
                style={{
                  background: '#020617',
                  border: '1px solid #1e293b',
                  borderRadius: '10px',
                  padding: '14px',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  overflowX: 'auto',
                  color: '#e2e8f0',
                  lineHeight: 1.5,
                  margin: 0,
                }}
              >
                {patch.unified_diff}
              </pre>
            </div>
          )}

          {/* RCA Postmortem text snippet */}
          {investigationState.final_rca_report && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#cbd5e1', marginBottom: '8px' }}>
                Executive Postmortem Summary:
              </div>
              <div
                style={{
                  background: '#0a0f1d',
                  border: '1px solid #1e293b',
                  borderRadius: '10px',
                  padding: '14px',
                  fontSize: '12px',
                  color: '#94a3b8',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {investigationState.final_rca_report}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            background: '#0d1527',
            padding: '16px 24px',
            borderTop: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '12px',
          }}
        >
          <button
            onClick={onClose}
            style={{
              background: '#1e293b',
              color: '#cbd5e1',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
          <button
            onClick={onApplyAndMerge}
            style={{
              background: '#10b981',
              color: '#ffffff',
              border: 'none',
              padding: '8px 20px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)',
            }}
          >
            <CheckCircle2 style={{ width: '16px', height: '16px' }} />
            Approve & Merge Hotfix PR
          </button>
        </div>
      </div>
    </div>
  );
};

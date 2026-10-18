import React, { useEffect, useRef } from 'react';
import { Terminal, CheckCircle2, XCircle, Search, Cpu, Wrench } from 'lucide-react';

export interface ThoughtStep {
  step_id: string;
  role: 'TRIAGE' | 'INVESTIGATOR' | 'SKEPTIC' | 'REMEDIATOR';
  thought: string;
  tool_name?: string;
  tool_input?: Record<string, any>;
  tool_output?: Record<string, any>;
  timestamp: string;
}

interface LiveAgentStreamProps {
  thoughts: ThoughtStep[];
  isStreaming: boolean;
}

export const LiveAgentStream: React.FC<LiveAgentStreamProps> = ({ thoughts, isStreaming }) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts]);

  const getRoleBadge = (role: ThoughtStep['role']) => {
    switch (role) {
      case 'TRIAGE':
        return { label: 'TRIAGE', bg: '#7c3aed', icon: <Search className="w-3 h-3" /> };
      case 'INVESTIGATOR':
        return { label: 'INVESTIGATOR', bg: '#2563eb', icon: <Cpu className="w-3 h-3" /> };
      case 'SKEPTIC':
        return { label: 'SKEPTIC', bg: '#db2777', icon: <XCircle className="w-3 h-3" /> };
      case 'REMEDIATOR':
        return { label: 'REMEDIATOR', bg: '#059669', icon: <Wrench className="w-3 h-3" /> };
      default:
        return { label: 'AGENT', bg: '#475569', icon: <Terminal className="w-3 h-3" /> };
    }
  };

  return (
    <div
      style={{
        background: '#090d16',
        border: '1px solid #1e293b',
        borderRadius: '16px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: '400px',
        overflow: 'hidden',
      }}
    >
      {/* Terminal Header */}
      <div
        style={{
          background: '#0d1527',
          padding: '12px 16px',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal style={{ width: '16px', height: '16px', color: '#38bdf8' }} />
          <span style={{ fontWeight: 700, fontSize: '13px', color: '#f8fafc' }}>
            Autonomous SRE Swarm Thought Stream
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: isStreaming ? '#10b981' : '#64748b',
              animation: isStreaming ? 'pulse 1.5s infinite' : 'none',
            }}
          />
          <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
            {isStreaming ? 'STREAMING ACTIVE' : 'IDLE'}
          </span>
        </div>
      </div>

      {/* Thought Log Body */}
      <div
        style={{
          padding: '16px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          flex: 1,
          fontFamily: 'monospace',
          fontSize: '12px',
        }}
      >
        {thoughts.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#475569',
              textAlign: 'center',
              gap: '8px',
            }}
          >
            <Terminal style={{ width: '32px', height: '32px', opacity: 0.4 }} />
            <div>No active investigation stream.</div>
            <div style={{ fontSize: '11px', color: '#334155' }}>
              Inject a chaos scenario above and click &quot;Launch SRE Swarm&quot; to see real-time agent reasoning.
            </div>
          </div>
        ) : (
          thoughts.map((step) => {
            const badge = getRoleBadge(step.role);
            return (
              <div
                key={step.step_id}
                style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid #1e293b',
                  borderRadius: '10px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        background: badge.bg,
                        color: '#fff',
                        fontSize: '10px',
                        fontWeight: 800,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        letterSpacing: '0.05em',
                      }}
                    >
                      {badge.label}
                    </span>
                    {step.tool_name && (
                      <span style={{ color: '#94a3b8', fontSize: '11px' }}>
                        tool: <strong style={{ color: '#38bdf8' }}>{step.tool_name}()</strong>
                      </span>
                    )}
                  </div>
                  <span style={{ color: '#475569', fontSize: '10px' }}>
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div style={{ color: '#e2e8f0', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {step.thought}
                </div>

                {step.tool_output && step.tool_output.ast_findings && (
                  <div
                    style={{
                      background: 'rgba(2, 6, 23, 0.8)',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      padding: '8px 10px',
                      marginTop: '4px',
                    }}
                  >
                    <div style={{ color: '#f43f5e', fontWeight: 700, fontSize: '11px', marginBottom: '4px' }}>
                      AST Analysis Inspector Output:
                    </div>
                    <div style={{ color: '#94a3b8', fontSize: '11px' }}>
                      Commit: <span style={{ color: '#f1f5f9' }}>{step.tool_output.ast_findings.commit_hash}</span> |
                      Author: <span style={{ color: '#f1f5f9' }}>{step.tool_output.ast_findings.author}</span>
                    </div>
                    {step.tool_output.ast_findings.violations?.map((v: any, idx: number) => (
                      <div key={idx} style={{ marginTop: '4px', color: '#fb7185', fontSize: '11px' }}>
                        • [{v.violation_type}] line {v.line_number}: {v.explanation}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};

import React from 'react';
import { Flame, Play, RefreshCw, ShieldAlert, Cpu } from 'lucide-react';

interface Scenario {
  id: string;
  title: string;
  service: string;
  description: string;
}

interface ChaosControlPanelProps {
  scenarios: Scenario[];
  activeIncident: any | null;
  isInvestigating: boolean;
  onInject: (scenarioId: string) => void;
  onReset: () => void;
  onStartInvestigation: () => void;
}

export const ChaosControlPanel: React.FC<ChaosControlPanelProps> = ({
  scenarios,
  activeIncident,
  isInvestigating,
  onInject,
  onReset,
  onStartInvestigation,
}) => {
  return (
    <div
      style={{
        background: '#0d1527',
        border: '1px solid #1e293b',
        borderRadius: '16px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Flame style={{ width: '20px', height: '20px', color: '#f43f5e' }} />
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
            Chaos Outage Injection
          </h2>
        </div>

        <button
          onClick={onReset}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: '#1e293b',
            color: '#cbd5e1',
            border: '1px solid #334155',
            padding: '6px 12px',
            borderRadius: '8px',
            fontSize: '12px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#334155')}
          onMouseLeave={(e) => (e.currentTarget.style.background = '#1e293b')}
        >
          <RefreshCw style={{ width: '13px', height: '13px' }} />
          Reset Baseline
        </button>
      </div>

      {/* Scenario cards grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
        {scenarios.map((sc) => (
          <div
            key={sc.id}
            onClick={() => onInject(sc.id)}
            style={{
              background: '#090d16',
              border: activeIncident?.scenario_id === sc.id ? '2px solid #ef4444' : '1px solid #1e293b',
              borderRadius: '10px',
              padding: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#475569')}
            onMouseLeave={(e) =>
              (e.currentTarget.style.borderColor = activeIncident?.scenario_id === sc.id ? '#ef4444' : '#1e293b')
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#f1f5f9' }}>{sc.title}</span>
              <span
                style={{
                  fontSize: '10px',
                  fontFamily: 'monospace',
                  background: '#1e293b',
                  color: '#94a3b8',
                  padding: '2px 6px',
                  borderRadius: '4px',
                }}
              >
                {sc.service}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '11px', color: '#64748b', lineHeight: 1.4 }}>
              {sc.description}
            </p>
          </div>
        ))}
      </div>

      {/* Active Alert Banner & Launch Investigation Button */}
      {activeIncident && (
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(15, 23, 42, 0.6))',
            border: '1px solid #ef4444',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
          }}
          className="glow-red"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <ShieldAlert style={{ width: '24px', height: '24px', color: '#ef4444', flexShrink: 0 }} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    background: '#ef4444',
                    color: '#fff',
                    fontSize: '10px',
                    fontWeight: 800,
                    padding: '2px 6px',
                    borderRadius: '4px',
                  }}
                >
                  {activeIncident.severity}
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                  {activeIncident.title}
                </span>
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                Firing Service: <span style={{ color: '#f43f5e', fontWeight: 600 }}>{activeIncident.firing_service}</span>{' '}
                | Metric: {activeIncident.metric_name} = {activeIncident.current_value} (Threshold: {activeIncident.threshold})
              </div>
            </div>
          </div>

          <button
            onClick={onStartInvestigation}
            disabled={isInvestigating}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: isInvestigating ? '#475569' : '#e11d48',
              color: '#ffffff',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '13px',
              cursor: isInvestigating ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 14px rgba(225, 29, 72, 0.4)',
              transition: 'all 0.2s ease',
              flexShrink: 0,
            }}
          >
            {isInvestigating ? (
              <>
                <Cpu style={{ width: '16px', height: '16px', animation: 'spin 1.5s linear infinite' }} />
                Swarm Analyzing...
              </>
            ) : (
              <>
                <Play style={{ width: '16px', height: '16px', fill: 'white' }} />
                Launch SRE Swarm
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Activity, Server, Database, HardDrive, Globe, AlertTriangle, CheckCircle2 } from 'lucide-react';

export interface ServiceNodeData {
  id: string;
  label: string;
  serviceType: 'GATEWAY' | 'SERVICE' | 'DATABASE' | 'CACHE' | 'THIRD_PARTY';
  status: 'HEALTHY' | 'DEGRADED' | 'FAILING';
  p99LatencyMs: number;
  errorRate: number;
  cpuPct: number;
  memoryPct: number;
  connPoolPct: number;
  metadata?: Record<string, any>;
}

export const CustomServiceNode = memo(({ data }: NodeProps<any>) => {
  const nodeData = data as ServiceNodeData;
  const isFailing = nodeData.status === 'FAILING';
  const isDegraded = nodeData.status === 'DEGRADED';
  const isHealthy = nodeData.status === 'HEALTHY';

  const getServiceIcon = () => {
    switch (nodeData.serviceType) {
      case 'GATEWAY':
        return <Globe className="w-4 h-4 text-sky-400" />;
      case 'DATABASE':
        return <Database className="w-4 h-4 text-emerald-400" />;
      case 'CACHE':
        return <HardDrive className="w-4 h-4 text-purple-400" />;
      case 'THIRD_PARTY':
        return <Activity className="w-4 h-4 text-amber-400" />;
      default:
        return <Server className="w-4 h-4 text-indigo-400" />;
    }
  };

  const getStatusBorder = () => {
    if (isFailing) return 'border-red-500 bg-red-950/40 animate-pulse-glow';
    if (isDegraded) return 'border-amber-500 bg-amber-950/30 glow-amber';
    return 'border-slate-800 bg-slate-900/90 hover:border-slate-700';
  };

  return (
    <div
      style={{
        minWidth: '220px',
        padding: '12px 14px',
        borderRadius: '12px',
        borderWidth: '2px',
        borderStyle: 'solid',
        backdropFilter: 'blur(8px)',
        transition: 'all 0.3s ease',
      }}
      className={`${getStatusBorder()}`}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#64748b' }} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {getServiceIcon()}
          <span style={{ fontWeight: 700, fontSize: '13px', color: '#f8fafc', letterSpacing: '-0.02em' }}>
            {nodeData.label}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {isHealthy && <CheckCircle2 style={{ width: '14px', height: '14px', color: '#10b981' }} />}
          {(isFailing || isDegraded) && (
            <AlertTriangle
              style={{
                width: '14px',
                height: '14px',
                color: isFailing ? '#ef4444' : '#f59e0b',
                animation: isFailing ? 'pulse 1s infinite' : 'none',
              }}
            />
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.7)',
          padding: '6px 8px',
          borderRadius: '8px',
          marginBottom: '8px',
        }}
      >
        <div>
          <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>P99 Latency</div>
          <div
            style={{
              fontSize: '12px',
              fontFamily: 'monospace',
              fontWeight: 700,
              color: nodeData.p99LatencyMs > 500 ? '#ef4444' : nodeData.p99LatencyMs > 50 ? '#f59e0b' : '#10b981',
            }}
          >
            {nodeData.p99LatencyMs.toFixed(1)}ms
          </div>
        </div>

        <div>
          <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Error Rate</div>
          <div
            style={{
              fontSize: '12px',
              fontFamily: 'monospace',
              fontWeight: 700,
              color: nodeData.errorRate > 5 ? '#ef4444' : '#10b981',
            }}
          >
            {nodeData.errorRate.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Resource Gauge */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#64748b' }}>
          <span>CPU: {nodeData.cpuPct}%</span>
          <span>Pool: {nodeData.connPoolPct}%</span>
        </div>
        <div style={{ width: '100%', height: '4px', background: '#1e293b', borderRadius: '2px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${Math.min(nodeData.connPoolPct, 100)}%`,
              height: '100%',
              background: nodeData.connPoolPct > 80 ? '#ef4444' : '#3b82f6',
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: '#64748b' }} />
    </div>
  );
});

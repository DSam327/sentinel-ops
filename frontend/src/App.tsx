import { useState, useEffect, useCallback } from 'react';
import { Node, Edge } from '@xyflow/react';
import { ShieldCheck, Activity, Cpu, Sparkles, BarChart3, Code2 } from 'lucide-react';
import { ServiceMeshGraph } from './components/ServiceMeshGraph';
import { ChaosControlPanel } from './components/ChaosControlPanel';
import { LiveAgentStream, ThoughtStep } from './components/LiveAgentStream';
import { RcaModal } from './components/RcaModal';
import { BenchmarkModal } from './components/BenchmarkModal';
import { ASTPlaygroundModal } from './components/ASTPlaygroundModal';

export function App() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [activeIncident, setActiveIncident] = useState<any | null>(null);
  const [thoughts, setThoughts] = useState<ThoughtStep[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationState, setInvestigationState] = useState<any | null>(null);
  const [isRcaModalOpen, setIsRcaModalOpen] = useState(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [isASTPlaygroundOpen, setIsASTPlaygroundOpen] = useState(false);

  // Fetch Topology
  const fetchTopology = useCallback(async () => {
    try {
      const res = await fetch('/api/topology');
      if (res.ok) {
        const data = await res.json();
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
      }
    } catch (e) {
      console.error('Failed to fetch topology:', e);
    }
  }, []);

  // Fetch Scenarios & Active Incident
  const fetchInitialData = useCallback(async () => {
    try {
      const [scRes, incRes] = await Promise.all([
        fetch('/api/scenarios'),
        fetch('/api/incident/active'),
      ]);
      if (scRes.ok) setScenarios(await scRes.json());
      if (incRes.ok) {
        const incData = await incRes.json();
        setActiveIncident(incData.active_incident);
      }
    } catch (e) {
      console.error('Failed to fetch initial data:', e);
    }
  }, []);

  useEffect(() => {
    fetchTopology();
    fetchInitialData();
    const interval = setInterval(fetchTopology, 3000);
    return () => clearInterval(interval);
  }, [fetchTopology, fetchInitialData]);

  // Inject Fault Scenario
  const handleInjectFault = async (scenarioId: string) => {
    try {
      const res = await fetch(`/api/chaos/inject/${scenarioId}`, { method: 'POST' });
      if (res.ok) {
        const alert = await res.json();
        setActiveIncident(alert);
        setThoughts([]);
        setInvestigationState(null);
        await fetchTopology();
      }
    } catch (e) {
      console.error('Failed to inject chaos:', e);
    }
  };

  // Reset to Baseline
  const handleResetMesh = async () => {
    try {
      const res = await fetch('/api/chaos/reset', { method: 'POST' });
      if (res.ok) {
        setActiveIncident(null);
        setThoughts([]);
        setInvestigationState(null);
        setIsRcaModalOpen(false);
        await fetchTopology();
      }
    } catch (e) {
      console.error('Failed to reset mesh:', e);
    }
  };

  // Launch Swarm Investigation via SSE Stream
  const handleStartInvestigation = async () => {
    if (!activeIncident || isInvestigating) return;

    setIsInvestigating(true);
    setIsStreaming(true);
    setThoughts([]);

    try {
      const eventSource = new EventSource('/api/agent/stream');

      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          eventSource.close();
          setIsStreaming(false);
          setIsInvestigating(false);
          // Fetch complete final state for RCA modal
          fetch('/api/agent/investigate', { method: 'POST' })
            .then((r) => r.json())
            .then((state) => {
              setInvestigationState(state);
              setIsRcaModalOpen(true);
            });
          return;
        }

        try {
          const thought: ThoughtStep = JSON.parse(event.data);
          setThoughts((prev) => [...prev, thought]);
        } catch (err) {
          console.error('Error parsing SSE event:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE connection error:', err);
        eventSource.close();
        setIsStreaming(false);
        setIsInvestigating(false);
      };
    } catch (err) {
      console.error('Failed to start stream:', err);
      setIsInvestigating(false);
      setIsStreaming(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#090d16', color: '#f8fafc' }}>
      {/* Top Navbar */}
      <header
        style={{
          background: '#0d1527',
          borderBottom: '1px solid #1e293b',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              background: 'linear-gradient(135deg, #e11d48, #9333ea)',
              color: 'white',
              padding: '8px',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ShieldCheck style={{ width: '22px', height: '22px' }} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 800, letterSpacing: '-0.02em', color: '#f8fafc' }}>
                SentinelOps
              </h1>
              <span
                style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '12px',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                }}
              >
                v1.0-ENTERPRISE
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>
              Autonomous SRE Swarm • Temporal GraphRAG • AST Static Analyzer • Subprocess Sandbox Runner
            </p>
          </div>
        </div>

        {/* System Action Tools & Capabilities */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setIsBenchmarkOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#1e293b',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <BarChart3 style={{ width: '14px', height: '14px' }} />
            Run Benchmark Evals
          </button>

          <button
            onClick={() => setIsASTPlaygroundOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: '#1e293b',
              color: '#c084fc',
              border: '1px solid rgba(192, 132, 252, 0.3)',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <Code2 style={{ width: '14px', height: '14px' }} />
            AST Live Playground
          </button>

          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: '#0f172a',
              color: '#94a3b8',
              border: '1px solid #1e293b',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontFamily: 'monospace',
            }}
          >
            <Activity style={{ width: '12px', height: '12px', color: '#10b981' }} />
            OTel Inferrer
          </span>
          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: '#0f172a',
              color: '#94a3b8',
              border: '1px solid #1e293b',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontFamily: 'monospace',
            }}
          >
            <Sparkles style={{ width: '12px', height: '12px', color: '#e11d48' }} />
            Adversarial Skeptic
          </span>
        </div>
      </header>

      {/* Main Split Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', flex: 1, overflow: 'hidden' }}>
        {/* Left Column: Chaos Control + React Flow Topology */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid #1e293b',
            overflow: 'hidden',
            padding: '16px',
            gap: '16px',
          }}
        >
          {/* Chaos Panel */}
          <ChaosControlPanel
            scenarios={scenarios}
            activeIncident={activeIncident}
            isInvestigating={isInvestigating}
            onInject={handleInjectFault}
            onReset={handleResetMesh}
            onStartInvestigation={handleStartInvestigation}
          />

          {/* Interactive React Flow Service Mesh */}
          <div
            style={{
              flex: 1,
              background: '#090d16',
              border: '1px solid #1e293b',
              borderRadius: '16px',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: '12px',
                left: '14px',
                zIndex: 5,
                fontSize: '12px',
                fontWeight: 700,
                color: '#64748b',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>LIVE SERVICE MESH TOPOLOGY</span>
              <span style={{ fontSize: '10px', color: '#334155' }}>(DRAG & ZOOM ENABLED)</span>
            </div>
            <ServiceMeshGraph nodes={nodes} edges={edges} />
          </div>
        </div>

        {/* Right Column: Terminal Agent Reasoning Stream */}
        <div style={{ padding: '16px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <LiveAgentStream thoughts={thoughts} isStreaming={isStreaming} />
        </div>
      </div>

      {/* Verified RCA Postmortem Modal */}
      <RcaModal
        isOpen={isRcaModalOpen}
        onClose={() => setIsRcaModalOpen(false)}
        onApplyAndMerge={handleResetMesh}
        investigationState={investigationState}
      />

      {/* Quantitative Evaluation Benchmark Modal */}
      <BenchmarkModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
      />

      {/* Interactive AST Static Analysis Playground */}
      <ASTPlaygroundModal
        isOpen={isASTPlaygroundOpen}
        onClose={() => setIsASTPlaygroundOpen(false)}
      />
    </div>
  );
}

export default App;

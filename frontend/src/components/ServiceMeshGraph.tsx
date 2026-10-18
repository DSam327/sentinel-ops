import React, { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  BackgroundVariant,
} from '@xyflow/react';
import { CustomServiceNode } from './CustomServiceNode';

interface ServiceMeshGraphProps {
  nodes: Node[];
  edges: Edge[];
}

export const ServiceMeshGraph: React.FC<ServiceMeshGraphProps> = ({ nodes, edges }) => {
  const nodeTypes = useMemo(() => ({ customServiceNode: CustomServiceNode }), []);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
        <Controls
          style={{
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#f8fafc',
          }}
        />
        <MiniMap
          nodeColor={(n: any) => {
            if (n.data?.status === 'FAILING') return '#ef4444';
            if (n.data?.status === 'DEGRADED') return '#f59e0b';
            return '#10b981';
          }}
          style={{
            background: '#090d16',
            border: '1px solid #1e293b',
            borderRadius: '8px',
          }}
        />
      </ReactFlow>
    </div>
  );
};

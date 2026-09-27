'use client';
import React from 'react';
import { AgentHub } from './AgentHub';

/**
 * Innovation-Lab workspace: an agent-first view.
 *
 * Pressing "Innovation Lab" shows ONLY the Agent Hub — the 19 discipline
 * agents grouped by category. Each agent opens a step-by-step guided flow.
 * Orchestration (multi-agent runs, projects, providers) stays available
 * through the Orchestrator smart-brief box in the hub.
 */
export function InnovationLabWorkspace() {
  return <AgentHub />;
}
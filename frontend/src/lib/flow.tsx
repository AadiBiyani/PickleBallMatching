import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

import type { FeedMethod, Scenario } from './types';

/** State carried through the record -> upload flow before a session exists. */
interface FlowState {
  feedMethod: FeedMethod;
  setFeedMethod: (m: FeedMethod) => void;
  /** Prototype-only: which demo scenario the next recorded session should follow. */
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
}

const FlowContext = createContext<FlowState | null>(null);

export function FlowProvider({ children }: { children: ReactNode }) {
  const [feedMethod, setFeedMethod] = useState<FeedMethod>('human_feeder');
  const [scenario, setScenario] = useState<Scenario>('normal');
  const value = useMemo(
    () => ({ feedMethod, setFeedMethod, scenario, setScenario }),
    [feedMethod, scenario],
  );
  return <FlowContext.Provider value={value}>{children}</FlowContext.Provider>;
}

export function useFlow(): FlowState {
  const ctx = useContext(FlowContext);
  if (!ctx) throw new Error('useFlow must be used inside FlowProvider');
  return ctx;
}

import { createContext, useContext, useMemo } from 'react'
import type { ReactNode } from 'react'
import type { FactMap, SourceMap } from '../../features/workflow/researchTypes'

type EvidenceValue = { facts: FactMap; sources: SourceMap }

const EvidenceCtx = createContext<EvidenceValue>({ facts: {}, sources: {} })

export function EvidenceProvider({
  facts,
  sources,
  children,
}: {
  facts: FactMap | null | undefined
  sources: SourceMap | null | undefined
  children: ReactNode
}) {
  const value = useMemo(() => ({ facts: facts ?? {}, sources: sources ?? {} }), [facts, sources])
  return <EvidenceCtx.Provider value={value}>{children}</EvidenceCtx.Provider>
}

export const useEvidence = (): EvidenceValue => useContext(EvidenceCtx)

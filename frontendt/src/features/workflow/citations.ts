import type { Fact, FactMap, Source, SourceMap } from './researchTypes'

export type ResolvedCitation = {
  factId: string
  fact: Fact | null
  sources: Source[]
  bestTier: number
}

export const TIER_LABEL: Record<number, string> = {
  1: 'Regulatory filing',
  2: 'Company / official',
  3: 'Reputable news',
  4: 'Other web',
}

export function resolveCitations(
  ids: string[] | undefined | null,
  facts: FactMap | null | undefined,
  sources: SourceMap | null | undefined,
): ResolvedCitation[] {
  return (ids ?? []).map((factId) => {
    const fact = facts?.[factId] ?? null
    const srcs = (fact?.source_ids ?? [])
      .map((sid) => sources?.[sid])
      .filter((s): s is Source => Boolean(s))
    return { factId, fact, sources: srcs, bestTier: srcs.length ? Math.min(...srcs.map((s) => s.tier)) : 4 }
  })
}

export function groupFactsByCategory(facts: FactMap | null | undefined): Record<string, Fact[]> {
  const out: Record<string, Fact[]> = {}
  Object.values(facts ?? {}).forEach((f) => {
    ;(out[f.category] ??= []).push(f)
  })
  return out
}

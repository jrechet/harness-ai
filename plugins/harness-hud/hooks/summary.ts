import type { Hud, HudLevel, Reading } from '../types'

const MAX_TEXT = 200
const MAX_ROWS = 12

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isCount = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0

// A state file is text someone else wrote: one line, bounded, no control characters.
const text = (value: unknown): string =>
  typeof value === 'string'
    ? value.replace(/[\u0000-\u001f\u007f]+/g, ' ').trim().slice(0, MAX_TEXT)
    : ''

const labels = (checks: unknown[], keep: (check: Record<string, unknown>) => boolean): string[] =>
  checks
    .filter(isObject)
    .filter(keep)
    .map(check => text(check.label))
    .filter(label => label !== '')
    .slice(0, MAX_ROWS)

const level = (raw: unknown): HudLevel | null => {
  if (!isObject(raw) || !isCount(raw.level) || !isCount(raw.passed_checks) || !isCount(raw.total_checks)) {
    return null
  }
  const checks = Array.isArray(raw.checks) ? raw.checks : []

  return {
    level: raw.level,
    name: text(raw.name),
    passed: raw.passed_checks,
    total: raw.total_checks,
    isAchieved: raw.achieved === true,
    isInScope: raw.in_scope !== false,
    missing: labels(checks, check => check.passed !== true && check.ignored !== true),
    setAside: labels(checks, check => check.ignored === true),
  }
}

/** The summary of a state file's text, or `unreadable` when it is not a `harness-state/1` file. */
export const summarise = (raw: string): Reading => {
  let state: unknown
  try {
    state = JSON.parse(raw)
  } catch {
    return { kind: 'unreadable' }
  }
  if (!isObject(state) || state.schema !== 'harness-state/1' || !isObject(state.level) || !Array.isArray(state.levels)) {
    return { kind: 'unreadable' }
  }
  if (!isCount(state.level.reached)) {
    return { kind: 'unreadable' }
  }
  const levels = state.levels.map(level)
  if (levels.some(one => one === null)) {
    return { kind: 'unreadable' }
  }
  const target = isObject(state.target) && isCount(state.target.level) ? state.target.level : null
  const hud: Hud = {
    date: text(state.date),
    reached: state.level.reached,
    reachedName: text(state.level.name),
    target,
    isTargetReached: isObject(state.target) && state.target.reached === true,
    levels: (levels as HudLevel[]).filter(one => one.level > 0).slice(0, MAX_ROWS),
    nextActions: (Array.isArray(state.next_actions) ? state.next_actions : []).map(text).filter(one => one !== '').slice(0, 3),
  }

  return { kind: 'read', hud }
}

/** The level the repository works towards: the first one in scope it has not reached. */
export const nextLevel = (hud: Hud): HudLevel | null =>
  hud.levels.find(one => one.isInScope && !one.isAchieved && (hud.target === null || one.level <= hud.target)) ?? null

/** One line for the row above the prompt. */
export const headline = (hud: Hud): string => {
  const here = `harness · level ${hud.reached}${hud.reachedName ? ` ${hud.reachedName}` : ''}`
  const next = nextLevel(hud)
  if (next === null) {
    return hud.target !== null ? `${here} · target reached` : `${here} · every level held`
  }

  return `${here} · level ${next.level}: ${next.passed} of ${next.total} checks`
}

/** One level as a row of text: its checks as filled and empty marks, then the count. */
export const ladderRow = (one: HudLevel): string => {
  const held = Math.min(one.passed, one.total)
  const marks = '■'.repeat(held) + '□'.repeat(one.total - held)
  const state = one.isAchieved ? ' · held' : one.isInScope ? '' : ' · beyond the target'

  return `${one.level} ${one.name}  ${marks} ${held}/${one.total}${state}`
}

export type HudLevel = {
  level: number
  name: string
  passed: number
  total: number
  isAchieved: boolean
  isInScope: boolean
  missing: string[]
  setAside: string[]
}

/** What the HUD draws: a summary of `.harness/state.json`, nothing else. */
export type Hud = {
  date: string
  reached: number
  reachedName: string
  target: number | null
  isTargetReached: boolean
  levels: HudLevel[]
  nextActions: string[]
}

/** `absent`: no state file, so nothing is drawn. `unreadable`: a file that is not the expected shape. */
export type Reading =
  | { kind: 'absent' }
  | { kind: 'unreadable' }
  | { kind: 'read'; hud: Hud }

declare module 'claude-code' {
  interface PluginState {
    'harness-hud': { reading: Shaped<Reading>; isHidden: boolean }
  }
}

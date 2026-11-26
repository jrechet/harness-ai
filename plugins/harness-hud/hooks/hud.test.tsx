import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { headline, ladderRow, summarise } from './summary'

const check = (label: string, passed: boolean, ignored = false) => ({ id: 'x', label, passed, ignored })
const STATE = {
  schema: 'harness-state/1',
  date: '2026-11-22',
  level: { reached: 1, name: 'Framed', next: 2 },
  target: { level: 3, name: 'Tooled', reached: false },
  levels: [
    { level: 0, name: 'None', achieved: true, in_scope: true, checks: [], passed_checks: 0, total_checks: 0 },
    { level: 1, name: 'Framed', achieved: true, in_scope: true, passed_checks: 5, total_checks: 5,
      checks: [check('An instruction file exists', true)] },
    { level: 2, name: 'Looped', achieved: false, in_scope: true, passed_checks: 2, total_checks: 4,
      checks: [check('A maintenance section', true), check('A harvest ran', false), check('A rule cites its check', false, true)] },
    { level: 3, name: 'Tooled', achieved: false, in_scope: true, passed_checks: 0, total_checks: 3,
      checks: [check('A hook formats', false)] },
    { level: 4, name: 'Delegated', achieved: false, in_scope: false, passed_checks: 0, total_checks: 2, checks: [] },
  ],
  next_actions: ['Run harness-harvest and merge its PR.'],
  facts: { instructions: { path: '/Users/someone/private' } },
}
const BAND = {
  plugin: 'harness-hud',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isCollapsed: false, isWorking: false, maxRows: 4, bodyColumns: 80, scroll: { offset: 0, bodyRows: 4 }, view: {} },
} as const
const PANE = {
  plugin: 'harness-hud',
  component: 'Pane',
  requestId: 'harness-hud',
  props: { title: 'Harness', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 30 }, view: {} },
} as const
const SURFACES = ['terminal', 'desktop', 'vscode', 'mobile'] as const

type Bottom = Parameters<TestBody>[1]

// Stands for the engine: a repository whose state file holds `text`, or has none.
const repository = (on: Bottom, text: string | null) => {
  const asked: string[] = []
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('fs.exists', (_, e) => {
    asked.push(e.path)

    return { value: text !== null }
  })
  on('fs.read', (_, e) => {
    asked.push(e.path)

    return { value: text ?? '' }
  })

  return asked
}

test('the summary keeps the ladder and drops everything else', () => {
  const read = summarise(JSON.stringify(STATE))

  expect(read.kind).toBe('read')
  if (read.kind !== 'read') return
  expect(read.hud.reached).toBe(1)
  expect(read.hud.target).toBe(3)
  expect(read.hud.levels.map(one => one.level)).toEqual([1, 2, 3, 4])
  expect(read.hud.levels[1]?.missing).toEqual(['A harvest ran'])
  expect(read.hud.levels[1]?.setAside).toEqual(['A rule cites its check'])
  expect(JSON.stringify(read)).not.toContain('/Users/someone')
})

test('the headline names the level reached and the next one in scope', () => {
  const read = summarise(JSON.stringify(STATE))
  if (read.kind !== 'read') throw new Error('not read')

  expect(headline(read.hud)).toBe('harness · level 1 Framed · level 2: 2 of 4 checks')
})

test('a target that is reached is said, and nothing beyond it is announced', () => {
  const reached = { ...STATE, level: { reached: 1, name: 'Framed' }, target: { level: 1, reached: true } }
  const read = summarise(JSON.stringify(reached))
  if (read.kind !== 'read') throw new Error('not read')

  expect(headline(read.hud)).toBe('harness · level 1 Framed · target reached')
})

test('a level with more checks passed than it has is drawn within its total', () => {
  expect(ladderRow({ level: 2, name: 'Looped', passed: 9, total: 3, isAchieved: false, isInScope: true, missing: [], setAside: [] })).toBe('2 Looped  ■■■ 3/3')
})

test('a file of another shape is unreadable, never half read', () => {
  for (const text of ['', '{', '[]', '"x"', '{"schema":"other/1"}',
    JSON.stringify({ ...STATE, levels: [{ level: 'two' }] }),
    JSON.stringify({ ...STATE, level: { reached: -1 } })]) {
    expect(summarise(text)).toEqual({ kind: 'unreadable' })
  }
})

test('a label from the file is one bounded line', () => {
  const noisy = { ...STATE, next_actions: ['first\nsecond\u001b[31m' + 'x'.repeat(500)] }
  const read = summarise(JSON.stringify(noisy))
  if (read.kind !== 'read') throw new Error('not read')

  const [action = ''] = read.hud.nextActions

  expect(action).not.toMatch(/[\n\u001b]/)
  expect(action.length).toBeLessThanOrEqual(200)
})

test('the row above the prompt says where the repository stands', async ($, on) => {
  const asked = repository(on, JSON.stringify(STATE))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...BAND, surface })

    expect((await ui.find({ type: 'Text', text: /harness/ }))?.text).toMatch(/level 1 Framed · level 2: 2 of 4 checks/)
    await ui.unmount()
  }
  expect(asked.length).toBeGreaterThan(0)
  expect(asked.every(path => path.endsWith('.harness/state.json'))).toBe(true)
})

test('a repository without a harness gets no row', async ($, on) => {
  repository(on, null)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })

  expect(await ui.find({ type: 'Text', text: /harness/ })).toBeUndefined()
  expect(await ui.find({ type: 'Button' })).toBeUndefined()
  await ui.unmount()
})

test('an unreadable state file gets no row, and the pane says so', async ($, on) => {
  repository(on, '{ not json')
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const band = await $.ui.mount({ ...BAND, surface: 'desktop' })

  expect(await band.find({ type: 'Button' })).toBeUndefined()
  await band.unmount()
  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })

  expect(await pane.find({ type: 'Text', text: /not a state file/ })).toBeDefined()
  await pane.unmount()
})

test('Hide takes the row away', async ($, on) => {
  repository(on, JSON.stringify(STATE))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  await ui.press({ key: 'hide' })

  expect(await ui.find({ type: 'Text', text: /harness/ })).toBeUndefined()
  await ui.unmount()
})

test('the pane shows the ladder, what is missing, what was set aside and the next step', async ($, on) => {
  repository(on, JSON.stringify(STATE))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...PANE, surface })

    expect((await ui.find({ type: 'Text', text: /2 Looped/ }))?.text).toBe('2 Looped  ■■□□ 2/4')
    expect((await ui.find({ type: 'Text', text: /1 Framed/ }))?.text).toBe('1 Framed  ■■■■■ 5/5 · held')
    expect((await ui.find({ type: 'Text', text: /4 Delegated/ }))?.text).toMatch(/beyond the target/)
    expect(await ui.find({ type: 'Text', text: /Target: level 3 · measured on 2026-11-22/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Missing for level 2/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /A harvest ran/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /A rule cites its check/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Run harness-harvest/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /A hook formats/ })).toBeUndefined()
    await ui.unmount()
  }
})

test('the pane of a repository without a harness says so', async ($, on) => {
  repository(on, null)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })

  expect(await ui.find({ type: 'Text', text: /No harness state/ })).toBeDefined()
  await ui.unmount()
})

test('a state file that changes is read again when a turn ends', async ($, on) => {
  let text = JSON.stringify(STATE)
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('fs.exists', () => ({ value: true }))
  on('fs.read', () => ({ value: text }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  text = JSON.stringify({ ...STATE, level: { reached: 2, name: 'Looped' } })
  await $.turn.complete({ reason: 'answer', answer: 'done', durationMs: 1, isAborted: false, turnId: 't1' })

  expect((await ui.find({ type: 'Text', text: /harness/ }))?.text).toMatch(/level 2 Looped/)
  await ui.unmount()
})

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
const RUN = { command: 'harness-hud', args: '', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 80 } } as const
const SURFACES = ['terminal', 'desktop', 'vscode', 'mobile'] as const

type Bottom = Parameters<TestBody>[1]

// Stands for the engine: a repository whose state file holds `text`, or has none.
const repository = (on: Bottom, text: string | null, opened: string[] = []) => {
  const asked: string[] = []
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('ui.open', (_, e) => {
    opened.push(e.id)

    return { value: { isPlaced: true } }
  })
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
    JSON.stringify({ ...STATE, schema: 'harness-state/2' }),
    JSON.stringify({ ...STATE, schema: undefined }),
    JSON.stringify({ ...STATE, levels: {} }),
    JSON.stringify({ ...STATE, level: 1 }),
    JSON.stringify({ ...STATE, levels: [{ ...STATE.levels[2], total_checks: 400000000 }] }),
    JSON.stringify({ ...STATE, levels: [{ ...STATE.levels[2], passed_checks: 1.5 }] }),
    JSON.stringify({ ...STATE, levels: [{ level: 'two' }] }),
    JSON.stringify({ ...STATE, level: { reached: -1 } })]) {
    expect(summarise(text)).toEqual({ kind: 'unreadable' })
  }
})

test('every text taken from the file is one bounded line, and the lists are bounded', () => {
  // A newline, an escape, the 8-bit CSI, a right-to-left override and a zero-width space.
  const noisy = 'first\nsecond\u001b[31m\u009b31m\u202egnp\u200b' + 'x'.repeat(500)
  const many = Array.from({ length: 20 }, (_, index) => check(`${noisy}${index}`, false))
  const read = summarise(JSON.stringify({
    ...STATE,
    date: noisy,
    level: { reached: 1, name: noisy },
    levels: [{ ...STATE.levels[2], name: noisy, checks: [...many, check(noisy, false, true)] }],
    next_actions: Array.from({ length: 20 }, () => noisy),
  }))
  if (read.kind !== 'read') throw new Error('not read')
  const [level] = read.hud.levels
  const texts = [read.hud.date, read.hud.reachedName, level?.name ?? '', ...(level?.missing ?? []), ...(level?.setAside ?? []), ...read.hud.nextActions]

  expect(texts.length).toBeGreaterThan(15)
  for (const one of texts) {
    expect(one).not.toMatch(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e]/)
    expect(one.length).toBeLessThanOrEqual(200)
    expect(one.length).toBeGreaterThan(0)
  }
  expect(read.hud.nextActions).toHaveLength(3)
  expect(level?.missing).toHaveLength(12)
  expect(headline(read.hud).length).toBeLessThan(80)
})

test('"target reached" is said only when the file says so', () => {
  const odd = summarise(JSON.stringify({ ...STATE, levels: [] }))
  if (odd.kind !== 'read') throw new Error('not read')

  expect(headline(odd.hud)).toBe('harness · level 1 Framed')
})

test('with no target and every level held, the headline says so', () => {
  const held = STATE.levels.map(one => ({ ...one, achieved: true, in_scope: true }))
  const read = summarise(JSON.stringify({ ...STATE, level: { reached: 4, name: 'Delegated' }, target: { level: null, reached: false }, levels: held }))
  if (read.kind !== 'read') throw new Error('not read')

  expect(headline(read.hud)).toBe('harness · level 4 Delegated · every level held')
})

test('the row above the prompt says where the repository stands', async ($, on) => {
  const asked = repository(on, JSON.stringify(STATE))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...BAND, surface })

    expect((await ui.find({ type: 'Text', text: /harness/ }))?.text).toMatch(/level 1 Framed · level 2: 2 of 4 checks/)
    await ui.unmount()
  }
  // The engine hands a path resolved against the folder the session started in.
  expect(asked.length).toBeGreaterThan(0)
  expect(new Set(asked).size).toBe(1)
  expect(asked[0]).toMatch(/^(\/[^/]+)*\/\.harness\/state\.json$/)
  expect(asked[0]).not.toContain('..')
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
    expect(await ui.find({ type: 'Text', text: /Target: level 3 · last changed on 2026-11-22/ })).toBeDefined()
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

test('/harness-hud opens the pane and brings a hidden row back', async ($, on) => {
  const opened: string[] = []
  repository(on, JSON.stringify(STATE), opened)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  await ui.press({ key: 'hide' })
  const ran = await $.command.run(RUN)

  expect(ran).toMatchObject({ text: 'Harness pane opened.' })
  expect(opened).toEqual(['harness-hud'])
  expect(await ui.find({ type: 'Text', text: /harness/ })).toBeDefined()
  await ui.unmount()
})

test('Details opens the pane', async ($, on) => {
  const opened: string[] = []
  repository(on, JSON.stringify(STATE), opened)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  await ui.press({ key: 'details' })

  expect(opened).toEqual(['harness-hud'])
  await ui.unmount()
})

test('a pane that cannot be placed is not announced as opened', async ($, on) => {
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('fs.exists', () => ({ value: false }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no surface' } }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

  expect(await $.command.run(RUN)).toMatchObject({ text: 'The harness pane could not be shown here.' })
})

test('the row stays out of the way of a survey', async ($, on) => {
  repository(on, JSON.stringify(STATE))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal', props: { ...BAND.props, hasSurvey: true } })

  expect(await ui.find({ type: 'Button' })).toBeUndefined()
  await ui.unmount()
})

test('a state file that cannot be read is unreadable, not absent', async ($, on) => {
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('fs.exists', () => ({ value: true }))
  on('fs.read', () => {
    throw new Error('denied')
  })
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })

  expect(await ui.find({ type: 'Text', text: /not a state file/ })).toBeDefined()
  await ui.unmount()
})

test('the pane says when the target is reached, and when there is none', async ($, on) => {
  let text = JSON.stringify({ ...STATE, target: { level: 1, reached: true } })
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('fs.exists', () => ({ value: true }))
  on('fs.read', () => ({ value: text }))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })

  expect(await ui.find({ type: 'Text', text: /Target level 1 reached/ })).toBeDefined()
  text = JSON.stringify({ ...STATE, target: { level: null, reached: false } })
  await $.turn.complete({ reason: 'answer', answer: 'done', durationMs: 1, isAborted: false, turnId: 't1' })

  expect(await ui.find({ type: 'Text', text: /No target level set/ })).toBeDefined()
  await ui.unmount()
})

test('the end of a sub-agent does not read the file again', async ($, on) => {
  let reads = 0
  on('command.register', () => ({ value: { command: 'harness-hud' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('fs.exists', () => ({ value: true }))
  on('fs.read', () => {
    reads += 1

    return { value: JSON.stringify(STATE) }
  })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const before = reads
  await $.turn.complete({ reason: 'answer', answer: 'done', durationMs: 1, isAborted: false, turnId: 't1', agentId: 'a1' })

  expect(reads).toBe(before)
  await $.turn.complete({ reason: 'answer', answer: 'done', durationMs: 1, isAborted: false, turnId: 't2' })

  expect(reads).toBe(before + 1)
})

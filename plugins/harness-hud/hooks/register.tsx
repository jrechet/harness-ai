import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Reading } from '../types'
import { headline, ladderRow, nextLevel, summarise } from './summary'

const PANE = 'harness-hud'
const TITLE = 'Harness'
const STATE_FILE = '.harness/state.json'
const ABSENT: Reading = { kind: 'absent' }

// Change the tag when the summary's fields change: it declines what an earlier version stored.
const reading = atom({ plugin: 'harness-hud', key: 'reading' } as const, ABSENT, { shape: 'reading-1' })
const isHidden = atom({ plugin: 'harness-hud', key: 'isHidden' } as const, false)

// Reads the state file of the working directory. It runs no command: the file is what
// `harness status` last wrote, and its date is shown so a stale one is seen as stale.
async function refresh($: EngineInterface): Promise<void> {
  let next: Reading = ABSENT
  try {
    if (await $.fs.exists(STATE_FILE)) {
      next = summarise(await $.fs.read(STATE_FILE))
    }
  } catch {
    next = { kind: 'unreadable' }
  }
  const before = await read($, reading)
  if (JSON.stringify(before) !== JSON.stringify(next)) {
    await update($, reading, () => next)
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'harness-hud',
      description: 'Show where this repository\'s AI harness stands, in a pane',
    })
    await refresh($)

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($)

    return next(e)
  })

  on('command.run', { command: 'harness-hud' }, async $ => {
    await refresh($)
    await update($, isHidden, () => false)
    await $.ui.open({ id: PANE, title: TITLE })

    return { text: 'Harness pane opened.' }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const now = await read($, reading)
    if (e.props.hasSurvey || now.kind !== 'read' || (await read($, isHidden))) {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)

    return (
      <Box>
        <Text dimColor>{headline(now.hud)} </Text>
        <Button key="details" label="Details" onPress={() => void $.ui.open({ id: PANE, title: TITLE })} />
        <Text> </Text>
        <Button key="hide" label="Hide" onPress={() => update($, isHidden, () => true)} />
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const now = await read($, reading)
    if (now.kind === 'absent') {
      return (
        <Box flexDirection="column">
          <Text>No harness state in this repository.</Text>
          <Text dimColor>The harness-ai plugin writes {STATE_FILE} when its status is measured.</Text>
        </Box>
      )
    }
    if (now.kind === 'unreadable') {
      return (
        <Box flexDirection="column">
          <Text>{STATE_FILE} is not a state file this pane can read.</Text>
          <Text dimColor>Measuring the status again rewrites it.</Text>
        </Box>
      )
    }
    const { hud } = now
    const towards = nextLevel(hud)

    return (
      <Box flexDirection="column">
        <Text bold>
          Level {hud.reached}
          {hud.reachedName ? ` · ${hud.reachedName}` : ''}
        </Text>
        <Text dimColor>
          {hud.target === null ? 'No target level set' : hud.isTargetReached ? `Target level ${hud.target} reached` : `Target: level ${hud.target}`}
          {hud.date ? ` · measured on ${hud.date}` : ''}
        </Text>
        <Text> </Text>
        {hud.levels.map(one => (
          <Text dimColor={!one.isInScope}>{ladderRow(one)}</Text>
        ))}
        {towards !== null && towards.missing.length > 0 && <Text> </Text>}
        {towards !== null && towards.missing.length > 0 && <Text bold>Missing for level {towards.level}</Text>}
        {towards !== null && towards.missing.map(label => <Text>· {label}</Text>)}
        {hud.levels.some(one => one.setAside.length > 0) && <Text> </Text>}
        {hud.levels.some(one => one.setAside.length > 0) && <Text bold>Set aside by you</Text>}
        {hud.levels.flatMap(one => one.setAside).map(label => (
          <Text dimColor>· {label}</Text>
        ))}
        {hud.nextActions.length > 0 && <Text> </Text>}
        {hud.nextActions.length > 0 && <Text bold>Next</Text>}
        {hud.nextActions.map(action => (
          <Text>· {action}</Text>
        ))}
      </Box>
    )
  })
}

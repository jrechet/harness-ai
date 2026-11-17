import { createApp, ref, computed, onMounted } from "./vendor/vue.esm-browser.prod.js";

const LEVEL_NAMES = ["None", "Framed", "Looped", "Verified", "Delegated"];

const fetchJson = async (url) => {
  const r = await fetch(url, { cache: "no-store" });
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || r.statusText);
  return body;
};

const Stairs = {
  props: ["levels", "reached", "target"],
  emits: ["select"],
  data: () => ({ selected: null }),
  methods: {
    pick(l) { this.selected = this.selected === l.level ? null : l.level; this.$emit("select", this.selected); },
  },
  template: `
    <div class="stairs" role="list">
      <button v-for="l in levels.filter(x => x.level)" :key="l.level" class="step" role="listitem"
              :class="{ achieved: l.achieved, next: !l.achieved && l.level === reached + 1 && l.in_scope !== false,
                        out: l.in_scope === false, target: l.level === target }"
              :aria-pressed="selected === l.level" :style="{ paddingTop: (6 + l.level * 8) + 'px' }" @click="pick(l)">
        <span class="num">Level {{ l.level }}</span>
        <span class="name">{{ l.name }}</span>
        <span class="goal" v-if="l.level === target">target</span>
        <span class="goal" v-else-if="l.in_scope === false">not targeted</span>
        <span class="count">{{ l.passed_checks }}/{{ l.total_checks }}</span>
        <span class="bar"><i :style="{ width: (100 * l.passed_checks / l.total_checks) + '%' }"></i></span>
      </button>
    </div>`,
};

const Checks = {
  props: ["level"],
  template: `
    <div v-if="level">
      <p class="summary">{{ level.summary }}</p>
      <p class="hint" v-if="level.in_scope === false">Not targeted: this level is not aimed for, nothing is proposed here. <code>harness target {{ level.level }}</code> to aim for it.</p>
      <ul class="checks">
        <li v-for="c in level.checks" :key="c.id">
          <span :class="c.passed ? 'ok' : 'ko'" :aria-label="c.passed ? 'passes' : 'fails'">{{ c.passed ? '✓' : '✗' }}</span>
          <span>{{ c.label }}
            <span class="value" v-if="c.value !== null && c.value !== undefined && typeof c.value !== 'object'"> · {{ c.value }}</span>
            <div class="action" v-if="!c.passed && level.in_scope !== false">→ {{ c.next_action }}</div>
          </span>
        </li>
      </ul>
    </div>`,
};

// History curve: one series (checks passed), level annotated at each point.
const History = {
  props: ["entries"],
  data: () => ({ hover: null, table: false }),
  computed: {
    W() { return 720; }, H() { return 200; }, pad() { return { l: 36, r: 16, t: 16, b: 28 }; },
    total() { return this.entries[0]?.checks_total || 18; },
    pts() {
      const n = this.entries.length, { l, r, t, b } = this.pad, w = this.W - l - r, h = this.H - t - b;
      return this.entries.map((e, i) => ({
        x: l + (n === 1 ? w / 2 : (w * i) / (n - 1)),
        y: t + h - (h * e.checks_passed) / this.total, e,
      }));
    },
    path() { return this.pts.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "); },
    ticks() { const { t, b } = this.pad, h = this.H - t - b; return [0, 0.5, 1].map(f => ({ y: t + h - h * f, v: Math.round(this.total * f) })); },
  },
  methods: {
    show(p, ev) { this.hover = { p, x: ev.clientX, y: ev.clientY }; },
    label(e) { return e.sha ? e.date : `${e.date} · not committed`; },
  },
  template: `
    <div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span class="hint" style="margin:0">Checks passed out of {{ total }}, at each committed <code>state.json</code></span>
        <button class="toggle" @click="table = !table">{{ table ? 'Chart' : 'Table' }}</button>
      </div>
      <table v-if="table" style="margin-top:8px">
        <thead><tr><th>Date</th><th>Level</th><th class="num">Checks</th><th>Commit</th></tr></thead>
        <tbody><tr v-for="e in entries" :key="e.sha || 'now'">
          <td>{{ e.date }}</td><td>{{ e.level }} · {{ names[e.level] }}</td>
          <td class="num">{{ e.checks_passed }}/{{ e.checks_total }}</td><td>{{ e.sha ? e.sha.slice(0,7) : 'current' }}</td>
        </tr></tbody>
      </table>
      <svg v-else class="chart" :viewBox="'0 0 ' + W + ' ' + H" role="img" aria-label="History of checks passed">
        <g class="grid"><line v-for="t in ticks" :key="t.v" :x1="pad.l" :x2="W - pad.r" :y1="t.y" :y2="t.y"/></g>
        <text v-for="t in ticks" :key="'l'+t.v" :x="pad.l - 6" :y="t.y + 4" text-anchor="end">{{ t.v }}</text>
        <path class="line" :d="path"/>
        <g v-for="p in pts" :key="p.e.sha || 'now'">
          <circle class="dot" :cx="p.x" :cy="p.y" r="4"/>
          <text class="label" :x="p.x" :y="p.y - 10" text-anchor="middle">Lv{{ p.e.level }}</text>
          <text :x="p.x" :y="H - 8" text-anchor="middle">{{ p.e.date.slice(5) }}</text>
          <rect class="hit" :x="p.x - 14" :y="pad.t" width="28" :height="H - pad.t - pad.b" @mousemove="show(p, $event)" @mouseleave="hover = null"/>
        </g>
      </svg>
      <div v-if="hover" class="tooltip" :style="{ left: hover.x + 'px', top: hover.y + 'px' }">
        {{ label(hover.p.e) }} · level {{ hover.p.e.level }} {{ names[hover.p.e.level] }} · {{ hover.p.e.checks_passed }}/{{ hover.p.e.checks_total }}
      </div>
    </div>`,
  created() { this.names = LEVEL_NAMES; },
};

// Horizontal bars per layer: total, of which misplaced (two series → legend + direct labels).
const Layers = {
  props: ["layers"],
  data: () => ({ hover: null }),
  computed: {
    rows() {
      return ["L1", "L2", "L3", "L4"].map(k => ({ k, ...(this.layers.layers[k] || { total: null, misplaced: null }) }));
    },
    max() { return Math.max(1, ...this.rows.map(r => r.total || 0)); },
    measured() { return this.layers.source === "audit"; },
  },
  methods: { show(r, ev) { this.hover = { r, x: ev.clientX, y: ev.clientY }; } },
  template: `
    <div>
      <div class="legend" v-if="measured"><span><i style="background:var(--series-1)"></i>items</span><span><i style="background:var(--serious)"></i>misplaced (verdict ≠ KEEP)</span></div>
      <svg class="chart" viewBox="0 0 720 150" role="img" aria-label="Items per layer">
        <g v-for="(r, i) in rows" :key="r.k" :transform="'translate(0,' + (i * 36 + 6) + ')'">
          <text x="0" y="17">{{ r.k }}</text>
          <template v-if="r.total === null">
            <rect class="bar-none" x="40" y="4" width="200" height="18" rx="4"/>
            <text x="248" y="17">unmeasured</text>
          </template>
          <template v-else>
            <rect class="bar-total" x="40" y="4" :width="Math.max(2, 480 * r.total / max)" height="18" rx="4"
                  @mousemove="show(r, $event)" @mouseleave="hover = null"/>
            <rect v-if="r.misplaced" class="bar-bad" x="40" y="4" :width="Math.max(2, 480 * r.misplaced / max)" height="18" rx="4"
                  @mousemove="show(r, $event)" @mouseleave="hover = null"/>
            <text class="label" :x="48 + 480 * r.total / max" y="17">{{ r.total }}<tspan v-if="r.misplaced"> · {{ r.misplaced }} misplaced</tspan></text>
          </template>
        </g>
      </svg>
      <p class="hint">{{ measured ? 'Measured by harness-audit on ' + layers.date + (layers.health_score != null ? ' · health score ' + layers.health_score : '') : layers.hint }}</p>
      <div v-if="hover" class="tooltip" :style="{ left: hover.x + 'px', top: hover.y + 'px' }">{{ hover.r.k }}: {{ hover.r.total }} item(s), {{ hover.r.misplaced || 0 }} misplaced</div>
    </div>`,
};

createApp({
  components: { Stairs, Checks, History, Layers },
  setup() {
    const state = ref(null), hist = ref([]), error = ref(null), selected = ref(null);
    const load = async () => {
      try {
        [state.value, hist.value] = await Promise.all([fetchJson("/api/state"), fetchJson("/api/history")]);
        error.value = null;
        // Do not open by default a level the user does not aim for: that would push them.
        if (selected.value === null) {
          const next = state.value.levels.find(l => l.level === state.value.level.next);
          selected.value = next && next.in_scope !== false ? next.level : state.value.level.reached || null;
        }
      } catch (e) { error.value = e.message; }
    };
    onMounted(() => { load(); setInterval(load, 10000); });
    const repoName = computed(() => state.value ? state.value.repo.split("/").filter(Boolean).pop() : "");
    const selectedLevel = computed(() => state.value?.levels.find(l => l.level === selected.value) || null);
    const facts = computed(() => state.value?.facts || null);
    const src = computed(() => facts.value?.instructions.source || {});
    const target = computed(() => state.value?.target || { level: null, reached: false });
    return { state, hist, error, selected, selectedLevel, repoName, facts, src, target, names: LEVEL_NAMES, load };
  },
  template: `
    <main>
      <p v-if="error" class="error">Cannot read the state: {{ error }}</p>
      <template v-if="state">
        <header>
          <h1>{{ repoName }}</h1>
          <span class="badge">Level {{ state.level.reached }} · {{ state.level.name }}</span>
          <span class="badge ok" v-if="target.reached">target reached</span>
          <span class="badge muted" v-else-if="target.level !== null">target: {{ target.level }} · {{ names[target.level] }}</span>
          <span class="badge muted" v-else>no target level</span>
          <span class="path">{{ state.repo }} · {{ state.date }}</span>
        </header>
        <div class="grid">
          <section class="card wide">
            <h2>Maturity levels</h2>
            <Stairs :levels="state.levels" :reached="state.level.reached" :target="target.level" @select="selected = $event"/>
            <Checks :level="selectedLevel"/>
            <p class="hint" v-if="!selectedLevel">Click a level to see its checks.</p>
          </section>
          <section class="card">
            <h2>Next actions</h2>
            <ol class="actions" v-if="state.next_actions.length"><li v-for="a in state.next_actions" :key="a">{{ a }}</li></ol>
            <p class="hint" v-else-if="target.reached">Target reached: the targeted level holds. Nothing to do.</p>
            <p class="hint" v-else-if="state.level.next === null">Nothing to do: highest level reached.</p>
            <p class="hint" v-else>Nothing to do within the targeted level.</p>
            <template v-if="state.dangling && state.dangling.length">
              <h2 style="margin-top:16px">References without a target</h2>
              <ul class="checks"><li v-for="d in state.dangling" :key="d.ref"><span class="ko" aria-label="not found">✗</span>
                <span><code>{{ d.ref }}</code> · line {{ d.line }} · {{ d.kind === 'contract' ? 'contract cited, SKILL.md not found' : d.kind === 'job' ? 'CI job cited, missing from the workflows' : 'guardrail cited, path not found' }}</span></li></ul>
            </template>
          </section>
          <section class="card facts">
            <h2>Measured facts</h2>
            <dl>
              <dt>Source file</dt><dd>{{ src.path || 'none' }}<span v-if="src.lines"> · {{ src.lines }} lines</span></dd>
              <dt>Mode</dt><dd>{{ src.mode || 'not declared' }}</dd>
              <dt>Rules</dt><dd>{{ src.rules_total ?? 0 }} · {{ src.rules_guarded ?? 0 }} enforced · {{ src.rules_justified ?? 0 }} justified · {{ src.rules_dated ?? 0 }} dated</dd>
              <dt>Oldest rule</dt><dd>{{ src.oldest_rule_date || 'no date' }}</dd>
              <dt>Last harvest</dt><dd>{{ facts.harvest_marker_age_days === null ? 'never' : facts.harvest_marker_age_days + ' d ago' }}</dd>
              <dt>Contracts</dt><dd>{{ facts.contracts.count }}</dd>
              <dt>Guardrails</dt><dd>{{ Object.keys(facts.guardrails.tools).join(', ') || 'none detected' }}</dd>
              <dt>CI</dt><dd>{{ facts.guardrails.workflows.length }} workflow(s)</dd>
            </dl>
          </section>
          <section class="card wide">
            <h2>History</h2>
            <History :entries="hist"/>
          </section>
          <section class="card wide">
            <h2>Layers L1–L4</h2>
            <Layers :layers="state.layers"/>
          </section>
        </div>
      </template>
    </main>`,
}).mount("#app");

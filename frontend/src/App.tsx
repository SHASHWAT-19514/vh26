import React, { useEffect, useRef, useState } from 'react';
import cytoscape, { Core } from 'cytoscape';
import { create } from 'zustand';
import './styles.css';
import { isValidAccount } from './validation';
import { api } from './api/client';

// Types
export type Node = {
  id: string;
  layer: string;
  hop: number;
  risk?: number;
  role?: string;
  tier?: string;
  bank?: string;
  ifsc?: string;
};

export type Edge = {
  id: string;
  from: string;
  to: string;
  amount: string;
  ts: string;
  hop: number;
  markers: string[];
  mode?: string;
  residual_paise?: number;
};

export type Trace = {
  trace_id: string;
  nodes: Node[];
  edges: Edge[];
  flow_links: any[];
  residuals: any[];
  timeline: any[];
  graph: any;
  stats: any;
};

type State = {
  view: string;
  dataset: any;
  trace?: Trace;
  evidence?: any;
  apiKey: string;
  selectedNode: Node | null;
  selectedEdge: Edge | null;
  isolatedNode: string | null;
  currentTimeIndex: number;
  isPlaying: boolean;
  activeCaseId: string | null;
  darkMode: boolean;
  set: (x: Partial<State>) => void;
};

const initialView = () => {
  const p = window.location.pathname;
  if (p.startsWith('/investigate')) return 'trace';
  if (p.startsWith('/cases')) return 'cases';
  if (p.startsWith('/timeline')) return 'trace';
  if (p.startsWith('/evidence') || p.startsWith('/documents')) return 'evidence';
  if (p.startsWith('/benchmarks')) return 'benchmarks';
  if (p.startsWith('/search')) return 'search';
  return 'overview';
};

export const useStore = create<State>((set) => ({
  view: initialView(),
  dataset: null,
  apiKey: localStorage.getItem('abhedya_api_key') || '',
  selectedNode: null,
  selectedEdge: null,
  isolatedNode: null,
  currentTimeIndex: 0,
  isPlaying: false,
  activeCaseId: null,
  darkMode: localStorage.getItem('abhedya_dark') === '1',
  set: (x) => set(x),
}));

// Layer Colors
const LAYER_COLORS: Record<string, string> = {
  VICTIM: '#3b82f6', // Blue
  L1: '#ef4444',     // Red (Collector Mule)
  L2: '#f59e0b',     // Amber (Distributor Mule)
  L3: '#8b5cf6',     // Purple (Terminal Cash-out)
};

// Role Badges
const ROLE_BADGES: Record<string, { label: string; color: string }> = {
  collector: { label: 'Collector Mule', color: '#ef4444' },
  distributor: { label: 'Distributor Mule', color: '#f59e0b' },
  terminal: { label: 'Terminal Cash-Out', color: '#8b5cf6' },
  suspected_mule: { label: 'Suspected Mule', color: '#ec4899' },
  none: { label: 'Standard Account', color: '#6b7280' },
};

function Sidebar() {
  const { view, set } = useStore();
  const navItems = [
    { id: 'overview', icon: '⌂', label: 'Command Center' },
    { id: 'trace', icon: '⌕', label: 'Investigate' },
    { id: 'search', icon: '🔍', label: 'Account Lookup' },
    { id: 'datasets', icon: '↥', label: 'Datasets' },
    { id: 'cases', icon: '◇', label: 'Cases' },
    { id: 'evidence', icon: '▣', label: 'Evidence & Reports' },
    { id: 'benchmarks', icon: '▤', label: 'Benchmarks' },
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="mark">◈</span>
        <div>
          <b>ABHEDYA</b>
          <small>CHAKRA / 1930</small>
        </div>
      </div>
      <div className="officer">
        <span className="avatar">OC</span>
        <div>
          <b>Officer Console</b>
          <small>Offline workstation</small>
        </div>
      </div>
      {navItems.map(({ id, icon, label }) => (
        <button
          className={view === id ? 'nav active' : 'nav'}
          onClick={() => set({ view: id })}
          key={id}
        >
          <span>{icon}</span>
          {label}
        </button>
      ))}
      <div className="side-foot">
        ● Offline mode
        <small>All evidence stays local</small>
      </div>
    </aside>
  );
}

function Header() {
  const { view, apiKey, darkMode, set } = useStore();
  const names: Record<string, string> = {
    overview: 'Overview',
    datasets: 'Datasets',
    trace: 'Trace a Victim',
    search: 'Account Search',
    cases: 'Case Management',
    evidence: 'Evidence & Reports',
    benchmarks: 'System Benchmarks',
  };
  const [draft, setDraft] = useState(apiKey);

  function toggleTheme() {
    const next = !darkMode;
    localStorage.setItem('abhedya_dark', next ? '1' : '0');
    set({ darkMode: next });
  }

  return (
    <header>
      <div>
        <small className="crumb">1930 CYBER CELL / {names[view] || 'Workspace'}</small>
        <h1>{view === 'overview' ? 'Good morning, Officer.' : names[view]}</h1>
      </div>
      <div className="header-tools">
        <span className="online">● System online</span>
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          title={darkMode ? 'Light mode' : 'Dark mode'}
        >
          {darkMode ? '☀' : '☾'}
        </button>
        <input
          aria-label="API key"
          placeholder="API key (optional)"
          type="password"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => {
            localStorage.setItem('abhedya_api_key', draft);
            set({ apiKey: draft });
          }}
        />
      </div>
    </header>
  );
}

function Overview() {
  const { set, apiKey, dataset } = useStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api('/api/metrics', {}, apiKey)
      .then((x) => set({ dataset: x.dataset }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiKey]);

  return (
    <>
      <section className="hero">
        <div>
          <small>YOUR INVESTIGATION DESK</small>
          <h2>
            Make the money trail
            <br />
            <em>easy to see.</em>
          </h2>
          <p>
            Trace a victim account across up to 4 hops, inspect multi-layer topologies,
            isolate suspect subgraphs, and seal verified findings into court-ready reports.
          </p>
          <button className="primary" onClick={() => set({ view: 'trace' })}>
            Open victim trace →
          </button>
        </div>
        <div className="rings">
          <i />
          <i />
          <i />
        </div>
      </section>

      <div className="section-title">
        <div>
          <small>AT A GLANCE</small>
          <h2>Investigation Health</h2>
        </div>
        <span className="pill">Live local data</span>
      </div>

      <div className="stats">
        {[
          ['TRANSACTIONS', dataset?.transactions || 0, 'green'],
          ['ACCOUNTS', dataset?.accounts || 0, 'blue'],
          ['FLAGGED ACCOUNTS', dataset?.flagged || 0, 'red'],
          ['ACTIVE RINGS', dataset?.rings || 0, 'purple'],
        ].map(([a, b, c]) => (
          <article className="stat" key={a as string}>
            <span className={'stat-icon ' + c}>◎</span>
            <small>{a}</small>
            <b>{loading ? '...' : Number(b).toLocaleString()}</b>
            <span>indexed records</span>
          </article>
        ))}
      </div>
    </>
  );
}

function Datasets() {
  const { apiKey, set } = useStore();
  const [file, setFile] = useState<File | undefined>();
  const [status, setStatus] = useState('');
  const [phase, setPhase] = useState<'idle' | 'uploading' | 'indexing' | 'done' | 'error'>('idle');
  const [uploadPct, setUploadPct] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  const loading = phase === 'uploading' || phase === 'indexing';

  function pickFile(f: File | undefined) {
    if (!f) return;
    setFile(f);
    setStatus('');
    setPhase('idle');
    setUploadPct(0);
  }

  function upload() {
    if (!file) { setStatus('Choose a CSV file first.'); return; }
    setPhase('uploading');
    setUploadPct(0);
    setStatus('');

    const fd = new FormData();
    fd.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/datasets/upload');
    if (apiKey) xhr.setRequestHeader('X-API-Key', apiKey);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) setUploadPct(Math.round((e.loaded / e.total) * 100));
    };

    xhr.upload.onload = () => {
      setUploadPct(100);
      setPhase('indexing');
    };

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          setStatus(`Indexed ${body.rows.toLocaleString()} rows · ${body.accounts.toLocaleString()} accounts`);
          setPhase('done');
          setTimeout(() => set({ view: 'trace' }), 1200);
        } else {
          setStatus(body?.error?.message || body?.detail || `HTTP ${xhr.status}`);
          setPhase('error');
        }
      } catch {
        setStatus(`HTTP ${xhr.status}`);
        setPhase('error');
      }
    };

    xhr.onerror = () => { setStatus('Network error — is the backend running?'); setPhase('error'); };
    xhr.send(fd);
  }

  const fmt = (b: number) => b > 1_048_576 ? `${(b / 1_048_576).toFixed(1)} MB` : `${(b / 1024).toFixed(0)} KB`;

  return (
    <>
      <div className="intro">
        <div>
          <small>DATA MANAGEMENT</small>
          <h2>Bring in your dataset</h2>
          <p>CSV is streamed to disk, processed by DuckDB, then analyzed with set-based SQL.</p>
        </div>
        <span className="pill green-pill">Private · offline</span>
      </div>
      <section className="card upload">
        <div className="upload-icon">↥</div>
        <div style={{ flex: 1 }}>
          <h3>Upload transaction CSV</h3>
          <p style={{ marginBottom: 18 }}>
            Required columns: <code>Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp</code> and more.
          </p>

          {/* Drop zone */}
          <label
            className={`drop${dragOver ? ' drop-active' : ''}${file ? ' drop-has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); pickFile(e.dataTransfer.files?.[0]); }}
          >
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
            {file ? (
              <>
                <span className="drop-file-name">📄 {file.name}</span>
                <small>{fmt(file.size)} · ready to upload</small>
              </>
            ) : (
              <>
                <span className="drop-hint">↥ Drag &amp; drop or click to browse</span>
                <small>CSV · 2M+ rows supported · processed locally</small>
              </>
            )}
          </label>

          {/* Progress bar */}
          {(loading || phase === 'done') && (
            <div className="upload-progress-wrap">
              <div className="upload-progress-header">
                <span>{phase === 'uploading' ? `Uploading… ${uploadPct}%` : phase === 'indexing' ? 'Indexing with DuckDB…' : '✓ Done'}</span>
                {phase === 'uploading' && <span>{uploadPct}%</span>}
              </div>
              <div className="upload-progress-track">
                <div
                  className={`upload-progress-bar${phase === 'indexing' ? ' indeterminate' : ''}`}
                  style={phase === 'uploading' ? { width: `${uploadPct}%` } : undefined}
                />
              </div>
            </div>
          )}

          {/* Status message */}
          {status && (
            <p className={`upload-status${phase === 'error' ? ' upload-status-error' : phase === 'done' ? ' upload-status-ok' : ''}`}>
              {status}
            </p>
          )}

          <button className="primary" onClick={upload} disabled={loading} style={{ marginTop: 16 }}>
            {loading ? 'Working…' : 'Upload & index →'}
          </button>
        </div>
      </section>
    </>
  );
}

function AccountSearch() {
  const { apiKey, set } = useStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [selectedAcct, setSelectedAcct] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');

  async function search() {
    if (!query.trim()) return;
    setLoading(true);
    setStatus('Searching accounts…');
    try {
      const res = await api(`/api/accounts/search?q=${encodeURIComponent(query.trim())}`, {}, apiKey);
      setResults(res.accounts || []);
      setStatus(`Found ${res.accounts?.length || 0} accounts`);
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(acctId: string) {
    setLoading(true);
    try {
      const res = await api(`/api/account/${acctId}`, {}, apiKey);
      setSelectedAcct(res);
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="intro">
        <div>
          <small>ACCOUNT INTELLIGENCE</small>
          <h2>Lookup Account Details</h2>
          <p>Search by account number prefix, inspect transaction history and risk contributors.</p>
        </div>
      </div>

      <div className="card trace-form">
        <label>
          Account Number Prefix
          <input
            placeholder="e.g. KKBK10000000"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
        </label>
        <button className="primary" onClick={search} disabled={loading}>
          {loading ? 'Searching…' : 'Search Accounts →'}
        </button>
        <span className="status">{status}</span>
      </div>

      {results.length > 0 && (
        <div className="card table-card">
          <h3>Search Results</h3>
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Bank</th>
                <th>In Txns</th>
                <th>Out Txns</th>
                <th>Risk Score</th>
                <th>Role</th>
                <th>Tier</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {results.map((a) => (
                <tr key={a.account}>
                  <td><b>{a.account}</b></td>
                  <td>{a.bank_code || '—'}</td>
                  <td>{a.incoming_count}</td>
                  <td>{a.outgoing_count}</td>
                  <td>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontWeight: 'bold',
                        backgroundColor: a.risk >= 60 ? '#fee2e2' : a.risk >= 40 ? '#fef3c7' : '#ecfdf5',
                        color: a.risk >= 60 ? '#b91c1c' : a.risk >= 40 ? '#b45309' : '#047857',
                      }}
                    >
                      {a.risk} / 100
                    </span>
                  </td>
                  <td>{a.role}</td>
                  <td>{a.tier}</td>
                  <td>
                    <button
                      className="secondary"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                      onClick={() => loadDetail(a.account)}
                    >
                      Inspect
                    </button>
                    <button
                      className="primary"
                      style={{ padding: '4px 8px', fontSize: '11px', marginLeft: '6px' }}
                      onClick={() => {
                        useStore.getState().set({ view: 'trace' });
                      }}
                    >
                      Trace
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedAcct && (
        <div className="card" style={{ marginTop: '16px' }}>
          <h3>Account Dossier: {selectedAcct.account}</h3>
          <div className="stats compact" style={{ margin: '12px 0' }}>
            <div className="stat">
              <small>RISK SCORE</small>
              <b>{selectedAcct.risk} / 100</b>
            </div>
            <div className="stat">
              <small>ROLE</small>
              <b>{selectedAcct.role}</b>
            </div>
            <div className="stat">
              <small>TOTAL INFLOW</small>
              <b>₹{(Number(selectedAcct.incoming_amount || 0) / 100).toLocaleString('en-IN')}</b>
            </div>
            <div className="stat">
              <small>TOTAL OUTFLOW</small>
              <b>₹{(Number(selectedAcct.outgoing_amount || 0) / 100).toLocaleString('en-IN')}</b>
            </div>
            <div className="stat">
              <small>UNIQUE SENDERS</small>
              <b>{selectedAcct.unique_senders}</b>
            </div>
            <div className="stat">
              <small>UNIQUE RECEIVERS</small>
              <b>{selectedAcct.unique_receivers}</b>
            </div>
          </div>

          <h4>Recent Transactions ({selectedAcct.transactions?.length || 0})</h4>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Txn ID</th>
                  <th>Timestamp</th>
                  <th>Sender</th>
                  <th>Receiver</th>
                  <th>Amount</th>
                  <th>Mode</th>
                  <th>Narration</th>
                  <th>IP / Device</th>
                </tr>
              </thead>
              <tbody>
                {selectedAcct.transactions?.slice(0, 50).map((t: any) => (
                  <tr key={t.transaction_id}>
                    <td><small>{t.transaction_id}</small></td>
                    <td><small>{t.timestamp}</small></td>
                    <td>{t.sender}</td>
                    <td>{t.receiver}</td>
                    <td><b>₹{(Number(t.amount_paise) / 100).toLocaleString('en-IN')}</b></td>
                    <td>{t.payment_mode}</td>
                    <td><small>{t.narration || '—'}</small></td>
                    <td><small>{t.ip} / {t.device}</small></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

function traceSubgraph(trace: Trace, root: string) {
  const nodeIds = new Set([root]);
  const edges = new Set<Edge>();
  let changed = true;
  while (changed) {
    changed = false;
    trace.edges.forEach((edge) => {
      if (!edges.has(edge) && (nodeIds.has(edge.from) || nodeIds.has(edge.to))) {
        edges.add(edge);
        nodeIds.add(edge.from);
        nodeIds.add(edge.to);
        changed = true;
      }
    });
  }
  return { nodes: trace.nodes.filter((node) => nodeIds.has(node.id)), edges: [...edges] };
}

function TraceView() {
  const {
    apiKey,
    set,
    trace,
    selectedNode,
    selectedEdge,
    isolatedNode,
    currentTimeIndex,
    isPlaying,
    darkMode,
  } = useStore();
  const [victim, setVictim] = useState('KKBK10000000');
  const [hops, setHops] = useState(4);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'graph' | 'layers' | 'topologies' | 'timeline' | 'evidence'>('graph');
  const [caseModalOpen, setCaseModalOpen] = useState(false);
  const [caseName, setCaseName] = useState('');
  const [activeLayerFilter, setActiveLayerFilter] = useState<string | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<any>(null);
  const [highlightMules, setHighlightMules] = useState(false);

  const graphRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core>();

  useEffect(() => {
    if (!selectedNode?.id) { setSelectedAccount(null); return; }
    let current = true;
    api(`/api/account/${encodeURIComponent(selectedNode.id)}`, {}, apiKey)
      .then((detail) => { if (current) setSelectedAccount(detail); })
      .catch(() => { if (current) setSelectedAccount(null); });
    return () => { current = false; };
  }, [selectedNode?.id, apiKey]);

  async function runTrace() {
    if (!isValidAccount(victim)) {
      setStatus('Account IDs must contain exactly 12 letters or digits');
      return;
    }
    setLoading(true);
    setStatus('Tracing money trail through DuckDB…');
    try {
      const x = await api(`/api/trace/${encodeURIComponent(victim)}?max_hops=${hops}`, {}, apiKey);
      set({
        trace: x,
        selectedNode: null,
        selectedEdge: null,
        isolatedNode: null,
        currentTimeIndex: x.timeline?.length ? x.timeline.length - 1 : 0,
      });
      setStatus('Trace complete');
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Build Cytoscape Graph with full interactivity
  useEffect(() => {
    if (!graphRef.current || !trace) return;

    cyRef.current?.destroy();

    const isDark = darkMode;
    const canvasBg   = isDark ? '#0d0f0e' : '#f8fafc';
    const labelColor = isDark ? '#e2e8e5' : '#18312d';
    const edgeLabelBg= isDark ? '#141716' : '#ffffff';
    const edgeLabelColor = isDark ? '#a0aaa6' : '#374151';

    // Mule layers – every non-VICTIM node is part of the mule chain
    const MULE_LAYERS = new Set(['L1', 'L2', 'L3']);

    // Determine nodes to display (filter if isolated)
    let displayNodes = trace.nodes;
    let displayEdges = trace.edges;

    if (isolatedNode) {
      const subgraph = traceSubgraph(trace, isolatedNode);
      displayNodes = subgraph.nodes;
      displayEdges = subgraph.edges;
    } else if (activeLayerFilter) {
      displayNodes = trace.nodes.filter((n) => n.layer === activeLayerFilter || n.layer === 'VICTIM');
      const nodeIds = new Set(displayNodes.map((n) => n.id));
      displayEdges = trace.edges.filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to));
    }

    // Time filter based on timeline index
    if (trace.timeline && trace.timeline.length > 0 && currentTimeIndex < trace.timeline.length - 1) {
      const maxTs = trace.timeline[currentTimeIndex]?.ts;
      if (maxTs) {
        displayEdges = displayEdges.filter((e) => e.ts <= maxTs);
        const activeEdgeNodeIds = new Set<string>();
        displayEdges.forEach((e) => {
          activeEdgeNodeIds.add(e.from);
          activeEdgeNodeIds.add(e.to);
        });
        displayNodes = displayNodes.filter((n) => n.id === victim || activeEdgeNodeIds.has(n.id));
      }
    }

    // mule chain: set of node IDs that are mule layers
    const muleNodeIds = new Set(displayNodes.filter((n) => MULE_LAYERS.has(n.layer)).map((n) => n.id));

    const elements = [
      ...displayNodes.map((n) => ({
        data: {
          id: n.id,
          label: n.id.length > 10 ? n.id.slice(0, 10) + '…' : n.id,
          fullLabel: n.id,
          layer: n.layer,
          risk: n.risk || 0,
          role: n.role || 'none',
          bank: n.bank || '',
          tier: n.tier || 'Low',
          color: LAYER_COLORS[n.layer] || '#c9ef79',
          isMule: MULE_LAYERS.has(n.layer) ? 1 : 0,
        },
      })),
      ...displayEdges.map((e) => ({
        data: {
          id: e.id,
          source: e.from,
          target: e.to,
          amount: e.amount,
          label: `₹${(Number(e.amount) / 100).toLocaleString('en-IN')}`,
          hop: e.hop,
          markers: e.markers,
          residual: e.residual_paise || 0,
          isMuleEdge: (muleNodeIds.has(e.from) || muleNodeIds.has(e.to)) ? 1 : 0,
        },
      })),
    ];

    const cy = cytoscape({
      container: graphRef.current,
      elements,
      style: [
        // ── Base node ──────────────────────────────────────────────────
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            'font-size': '9px',
            'font-weight': '700' as any,
            color: labelColor,
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 4,
            width: 42,
            height: 42,
            'border-width': 2.5,
            'border-color': 'data(color)',
            'overlay-opacity': 0,
            'text-outline-width': isDark ? 2 : 0,
            'text-outline-color': isDark ? '#0d0f0e' : 'transparent',
          },
        },
        // ── Victim node ────────────────────────────────────────────────
        {
          selector: 'node[layer = "VICTIM"]',
          style: {
            shape: 'ellipse',
            width: 48,
            height: 48,
            'background-color': '#3b82f6',
            'border-color': '#93c5fd',
            'border-width': 3,
            color: labelColor,
          },
        },
        // ── L1 Collector ───────────────────────────────────────────────
        {
          selector: 'node[layer = "L1"]',
          style: {
            'background-color': '#ef4444',
            'border-color': '#fca5a5',
          },
        },
        // ── L2 Distributor ─────────────────────────────────────────────
        {
          selector: 'node[layer = "L2"]',
          style: {
            'background-color': '#f59e0b',
            'border-color': '#fcd34d',
          },
        },
        // ── L3 Terminal ────────────────────────────────────────────────
        {
          selector: 'node[layer = "L3"]',
          style: {
            'background-color': '#8b5cf6',
            'border-color': '#c4b5fd',
          },
        },
        // ── Selected node ──────────────────────────────────────────────
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#fbbf24',
            'overlay-opacity': 0,
          },
        },
        // ── Base edge ──────────────────────────────────────────────────
        {
          selector: 'edge',
          style: {
            'line-color': isDark ? '#3a4a44' : '#c5d5cf',
            'target-arrow-color': isDark ? '#3a4a44' : '#c5d5cf',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            width: 1.5,
            label: 'data(label)',
            'font-size': '8px',
            'font-weight': '600' as any,
            color: edgeLabelColor,
            'text-background-color': edgeLabelBg,
            'text-background-opacity': 0.85,
            'text-background-padding': '3px' as any,
            'text-border-color': isDark ? '#252b28' : '#e5e7eb',
            'text-border-width': 1,
            'text-border-opacity': 1,
          },
        },
        // ── Mule chain edges (red solid) ───────────────────────────────
        {
          selector: 'edge[isMuleEdge = 1]',
          style: {
            'line-color': '#ef4444',
            'target-arrow-color': '#ef4444',
            width: 2.5,
          },
        },
        // ── Selected edge ──────────────────────────────────────────────
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#fbbf24',
            'target-arrow-color': '#fbbf24',
            width: 4,
          },
        },
        // ── Mule highlight ON: dim non-mule nodes ──────────────────────
        ...(highlightMules ? [
          {
            selector: 'node[isMule = 0]',
            style: {
              opacity: 0.15,
            },
          },
          {
            selector: 'node[isMule = 1]',
            style: {
              opacity: 1,
              'border-width': 4,
              'border-color': '#ef4444',
            },
          },
          {
            selector: 'edge[isMuleEdge = 0]',
            style: {
              opacity: 0.08,
            },
          },
          {
            selector: 'edge[isMuleEdge = 1]',
            style: {
              opacity: 1,
              'line-color': '#ef4444',
              'target-arrow-color': '#ef4444',
              width: 3,
            },
          },
        ] : []),
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 40,
        spacingFactor: 1.6,
      },
    });

    // apply canvas background directly
    if (graphRef.current) {
      graphRef.current.style.backgroundColor = canvasBg;
    }

    // Node click handler
    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data();
      const fullNode = trace.nodes.find((n) => n.id === nodeData.id) || nodeData;
      set({ selectedNode: fullNode, selectedEdge: null });
    });

    // Edge click handler
    cy.on('tap', 'edge', (evt) => {
      const edgeData = evt.target.data();
      const fullEdge = trace.edges.find((e) => e.id === edgeData.id) || edgeData;
      set({ selectedEdge: fullEdge, selectedNode: null });
    });

    // Canvas click (deselect)
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        set({ selectedNode: null, selectedEdge: null });
      }
    });

    cyRef.current = cy;
    return () => cy.destroy();
  }, [trace, isolatedNode, activeLayerFilter, currentTimeIndex, highlightMules, darkMode]);

  // Timeline Playback Animation
  useEffect(() => {
    let timer: any;
    if (isPlaying && trace?.timeline?.length) {
      timer = setInterval(() => {
        const nextIndex = currentTimeIndex + 1;
        if (nextIndex >= (trace.timeline?.length || 0)) {
          set({ currentTimeIndex: 0, isPlaying: false });
        } else {
          set({ currentTimeIndex: nextIndex });
        }
      }, 800);
    }
    return () => clearInterval(timer);
  }, [isPlaying, trace, currentTimeIndex]);

  // Create Case Handler
  async function handleCreateCase() {
    if (!trace) return;
    try {
      const caseRes = await api(
        '/api/cases',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ victim_account: victim, max_hops: hops }),
        },
        apiKey
      );
      setStatus(`Case created: ${caseRes.case_id}`);
      setCaseModalOpen(false);
    } catch (e: any) {
      setStatus(e.message);
    }
  }

  // Export Subgraph
  async function handleExportSubgraph(format: 'json' | 'csv') {
    if (!trace) return;
    const dataStr =
      format === 'json'
        ? JSON.stringify({ nodes: trace.nodes, edges: trace.edges }, null, 2)
        : 'source,target,amount,timestamp,hop\n' +
          trace.edges.map((e) => `${e.from},${e.to},${e.amount},${e.ts},${e.hop}`).join('\n');
    const blob = new Blob([dataStr], {
      type: format === 'json' ? 'application/json' : 'text/csv',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `subgraph-${victim}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Group nodes by layer
  const l1Nodes = trace?.nodes.filter((n) => n.layer === 'L1') || [];
  const l2Nodes = trace?.nodes.filter((n) => n.layer === 'L2') || [];
  const l3Nodes = trace?.nodes.filter((n) => n.layer === 'L3') || [];

  return (
    <>
      <div className="intro">
        <div>
          <small>MONEY TRAIL INVESTIGATION</small>
          <h2>Mule Chain & Multi-Hop Trace</h2>
          <p>Deterministic 4-hop money flow tracing with FIFO attribution, syndicate topologies, and temporal playback.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {trace && (
            <>
              <button
                className="secondary"
                style={{ padding: '6px 12px', fontSize: '12px' }}
                onClick={() => setCaseModalOpen(true)}
              >
                + Save as Case
              </button>
              <button
                className="secondary"
                style={{ padding: '6px 12px', fontSize: '12px' }}
                onClick={() => handleExportSubgraph('json')}
              >
                Export JSON
              </button>
              <button
                className="secondary"
                style={{ padding: '6px 12px', fontSize: '12px' }}
                onClick={() => handleExportSubgraph('csv')}
              >
                Export CSV
              </button>
            </>
          )}
        </div>
      </div>

      {/* Input controls */}
      <div className="card trace-form">
        <label>
          Victim Account
          <input
            maxLength={12}
            value={victim}
            onChange={(e) => setVictim(e.target.value)}
            placeholder="12-char account"
          />
        </label>
        <label>
          Max Hops
          <select value={hops} onChange={(e) => setHops(Number(e.target.value))}>
            <option value={4}>4 Hops (Full Chain)</option>
            <option value={3}>3 Hops</option>
            <option value={2}>2 Hops</option>
            <option value={1}>1 Hop (Direct)</option>
          </select>
        </label>
        <button className="primary" onClick={runTrace} disabled={loading}>
          {loading ? 'Tracing…' : 'Trace Money Trail →'}
        </button>
        <span className="status">{status}</span>
      </div>

      {trace ? (
        <>
          {/* Top KPI stats */}
          <div className="stats compact" style={{ marginTop: '16px' }}>
            <div className="stat">
              <small>TOTAL NODES</small>
              <b>{trace.stats.nodes}</b>
            </div>
            <div className="stat">
              <small>TRANSACTIONS</small>
              <b>{trace.stats.edges}</b>
            </div>
            <div className="stat">
              <small>TOTAL SIPHONED</small>
              <b>₹{(Number(trace.stats.total_siphoned || 0) / 100).toLocaleString('en-IN')}</b>
            </div>
            <div className="stat">
              <small>FIFO FLOW LINKS</small>
              <b>{trace.stats.flow_links}</b>
            </div>
            <div className="stat">
              <small>TRACE TIME</small>
              <b>{trace.stats.elapsed_ms} ms</b>
            </div>
          </div>

          {/* Navigation sub-tabs */}
          <div style={{ display: 'flex', gap: '8px', margin: '16px 0', borderBottom: '1px solid #e5e7eb', paddingBottom: '8px' }}>
            {[
              { id: 'graph', label: 'Interactive Graph' },
              { id: 'layers', label: `Mule Chain Layers (L1: ${l1Nodes.length} · L2: ${l2Nodes.length} · L3: ${l3Nodes.length})` },
              { id: 'topologies', label: 'Topologies & Risk Analysis' },
              { id: 'timeline', label: `Timeline Events (${trace.timeline?.length || 0})` },
              { id: 'evidence', label: 'FIFO Attribution & Residuals' },
            ].map((t) => (
              <button
                key={t.id}
                className={activeTab === t.id ? 'primary' : 'secondary'}
                style={{ padding: '6px 14px', fontSize: '12px' }}
                onClick={() => setActiveTab(t.id as any)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* TAB 1: INTERACTIVE GRAPH & CONTROLS */}
          {activeTab === 'graph' && (
            <div style={{ display: 'grid', gridTemplateColumns: selectedNode || selectedEdge ? '1fr 340px' : '1fr', gap: '16px' }}>
              <div className="card graph-card" style={{ position: 'relative', padding: '16px' }}>
                {/* ── Graph toolbar ────────────────────────────── */}
                <div className="graph-toolbar">
                  <div className="graph-toolbar-left">
                    <h3 style={{ margin: 0, fontSize: '14px' }}>Suspect Network Graph</h3>
                    {/* Legend dots */}
                    <div className="graph-legend">
                      {[
                        { color: '#3b82f6', label: 'Victim' },
                        { color: '#ef4444', label: 'L1 Collector' },
                        { color: '#f59e0b', label: 'L2 Distributor' },
                        { color: '#8b5cf6', label: 'L3 Terminal' },
                      ].map(({ color, label }) => (
                        <span key={label} className="graph-legend-item">
                          <span className="graph-legend-dot" style={{ background: color }} />
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="graph-toolbar-right">
                    {/* Mule highlight toggle */}
                    <button
                      className={`graph-btn${highlightMules ? ' graph-btn-active' : ''}`}
                      onClick={() => setHighlightMules((v) => !v)}
                      title="Highlight mule chain nodes; fade non-mule nodes"
                    >
                      <span className="graph-btn-dot" style={{ background: '#ef4444' }} />
                      {highlightMules ? 'Mule Chain ON' : 'Highlight Mule Chain'}
                    </button>

                    {/* Layer filter */}
                    <span className="graph-divider" />
                    <span style={{ fontSize: '10px', color: 'var(--muted)' }}>Filter:</span>
                    <button
                      className={`graph-btn${activeLayerFilter === null ? ' graph-btn-active' : ''}`}
                      onClick={() => setActiveLayerFilter(null)}
                    >All</button>
                    {['L1', 'L2', 'L3'].map((l) => (
                      <button
                        key={l}
                        className={`graph-btn${activeLayerFilter === l ? ' graph-btn-active' : ''}`}
                        style={activeLayerFilter === l ? { borderColor: LAYER_COLORS[l], color: LAYER_COLORS[l] } : {}}
                        onClick={() => setActiveLayerFilter(activeLayerFilter === l ? null : l)}
                      >{l}</button>
                    ))}
                    {isolatedNode && (
                      <button
                        className="graph-btn"
                        style={{ borderColor: '#ef4444', color: '#ef4444' }}
                        onClick={() => set({ isolatedNode: null })}
                      >Reset ✕</button>
                    )}
                  </div>
                </div>

                {/* Cytoscape Container */}
                <div ref={graphRef} className="cy graph-canvas" />

                {/* Temporal Playback Slider */}
                {trace.timeline && trace.timeline.length > 0 && (
                  <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f3f4f6', borderRadius: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontWeight: 'bold', fontSize: '12px' }}>Temporal Playback</span>
                      <span style={{ fontSize: '11px', color: '#4b5563' }}>
                        Step {currentTimeIndex + 1} of {trace.timeline.length} · {trace.timeline[currentTimeIndex]?.ts}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button
                        className="secondary"
                        style={{ padding: '4px 10px', fontSize: '12px' }}
                        onClick={() => set({ isPlaying: !isPlaying })}
                      >
                        {isPlaying ? '⏸ Pause' : '▶ Play'}
                      </button>
                      <input
                        type="range"
                        min={0}
                        max={trace.timeline.length - 1}
                        value={currentTimeIndex}
                        onChange={(e) => set({ currentTimeIndex: Number(e.target.value) })}
                        style={{ flex: 1 }}
                      />
                      <button
                        className="secondary"
                        style={{ padding: '4px 8px', fontSize: '11px' }}
                        onClick={() => set({ currentTimeIndex: trace.timeline.length - 1 })}
                      >
                        Latest
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Detail Inspection Sidebar (Node / Edge) */}
              {(selectedNode || selectedEdge) && (
                <div className="card" style={{ height: 'fit-content' }}>
                  {selectedNode && (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0 }}>Account Details</h3>
                        <button
                          className="secondary"
                          style={{ padding: '2px 6px', fontSize: '10px' }}
                          onClick={() => set({ selectedNode: null })}
                        >
                          ✕
                        </button>
                      </div>
                      <div style={{ margin: '12px 0' }}>
                        <b style={{ fontSize: '14px', wordBreak: 'break-all' }}>{selectedNode.id}</b>
                        <div style={{ marginTop: '6px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <span
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 'bold',
                              backgroundColor: LAYER_COLORS[selectedNode.layer] || '#e5e7eb',
                              color: '#ffffff',
                            }}
                          >
                            {selectedNode.layer}
                          </span>
                          <span
                            style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              backgroundColor: '#fee2e2',
                              color: '#b91c1c',
                              fontWeight: 'bold',
                            }}
                          >
                            Risk: {selectedNode.risk || 0}/100
                          </span>
                        </div>
                      </div>

                      <div style={{ fontSize: '12px', lineHeight: '1.6' }}>
                        <div><b>Role:</b> {selectedNode.role || 'Unclassified'}</div>
                        <div><b>Likely layer:</b> {selectedAccount?.detection?.role_label || selectedNode.layer}</div>
                        <div><b>Bank:</b> {selectedNode.bank || '—'}</div>
                        <div><b>IFSC:</b> {selectedNode.ifsc || '—'}</div>
                        <div><b>Hop Depth:</b> {selectedNode.hop}</div>
                      </div>

                      {selectedAccount && (
                        <div style={{ marginTop: '12px', fontSize: '11px', lineHeight: '1.6' }}>
                          <b>Explainable risk breakdown</b>
                          {[
                            ['Velocity', 'velocity_score', 25], ['Fan-in', 'fan_in_score', 15],
                            ['Fan-out', 'fan_out_score', 15], ['Layering', 'layering_score', 15],
                            ['Terminal', 'terminal_score', 10], ['Cycle', 'cycle_score', 10],
                            ['Behaviour', 'behaviour_score', 10],
                          ].map(([label, key, weight]) => (
                            <div key={key as string} style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span>{label}</span><b>{selectedAccount.risk_breakdown?.[key as string] ?? 0}/{weight}</b>
                            </div>
                          ))}
                          <div style={{ marginTop: '8px' }}><b>Velocity</b>: 3m {((selectedAccount.risk_breakdown?.three_minute_pass_through_ratio || 0) * 100).toFixed(1)}%, 15m {((selectedAccount.risk_breakdown?.fifteen_minute_pass_through_ratio || 0) * 100).toFixed(1)}%; median delay {selectedAccount.risk_breakdown?.median_pass_through_delay_seconds || 0}s</div>
                          <div><b>Fan-in:</b> {selectedAccount.unique_senders} senders · {selectedAccount.incoming_count} transfers</div>
                          <div><b>Fan-out:</b> {selectedAccount.unique_receivers} receivers · {selectedAccount.outgoing_count} transfers</div>
                          <div><b>Detection reasons</b></div>
                          {(selectedAccount.detection?.reasons || []).map((reason: string) => <div key={reason}>• {reason}</div>)}
                          <div><b>Collector evidence IDs:</b> {(selectedAccount.detection?.collector_evidence?.transaction_ids || []).join(', ') || '—'}</div>
                          <div><b>Velocity evidence IDs:</b> {(selectedAccount.risk_breakdown?.velocity_transaction_ids || []).join(', ') || '—'}</div>
                          <div><b>Terminal raw evidence:</b> {JSON.stringify(selectedAccount.risk_breakdown?.terminal_evidence || [])}</div>
                          <div><b>Cycle evidence:</b> {JSON.stringify(selectedAccount.risk_breakdown?.cycle_evidence || [])}</div>
                        </div>
                      )}

                      {/* One-click Subgraph Isolation */}
                      <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <button
                          className="primary"
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                          onClick={() => set({ isolatedNode: selectedNode.id })}
                        >
                          🔍 Isolate Connected Syndicate
                        </button>
                        <button
                          className="secondary"
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                          onClick={() => {
                            const subgraph = traceSubgraph(trace!, selectedNode.id);
                            const blob = new Blob([JSON.stringify({
                              root_account: selectedNode.id,
                              nodes: subgraph.nodes,
                              edges: subgraph.edges,
                              flow_links: trace!.flow_links.filter((link: any) => subgraph.edges.some((edge) => edge.id === link.target)),
                            }, null, 2)], { type: 'application/json' });
                            const url = URL.createObjectURL(blob);
                            const anchor = document.createElement('a');
                            anchor.href = url;
                            anchor.download = `subgraph-${selectedNode.id}.json`;
                            anchor.click();
                            URL.revokeObjectURL(url);
                          }}
                        >
                          Export Connected Evidence JSON
                        </button>
                      </div>
                    </>
                  )}

                  {selectedEdge && (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0 }}>Transaction Details</h3>
                        <button
                          className="secondary"
                          style={{ padding: '2px 6px', fontSize: '10px' }}
                          onClick={() => set({ selectedEdge: null })}
                        >
                          ✕
                        </button>
                      </div>
                      <div style={{ margin: '12px 0', fontSize: '12px', lineHeight: '1.6' }}>
                        <div><b>Txn ID:</b> <small>{selectedEdge.id}</small></div>
                        <div><b>From:</b> {selectedEdge.from}</div>
                        <div><b>To:</b> {selectedEdge.to}</div>
                        <div><b>Amount:</b> <b style={{ color: '#047857' }}>₹{(Number(selectedEdge.amount) / 100).toLocaleString('en-IN')}</b></div>
                        <div><b>Timestamp:</b> {selectedEdge.ts}</div>
                        <div><b>Hop Layer:</b> L{selectedEdge.hop}</div>
                        <div><b>Residual (Paise):</b> ₹{(Number(selectedEdge.residual_paise || 0) / 100).toLocaleString('en-IN')}</div>
                        <div>
                          <b>Flags / Markers:</b>
                          <div style={{ marginTop: '4px' }}>
                            {selectedEdge.markers?.length ? (
                              selectedEdge.markers.map((m) => (
                                <span key={m} style={{ padding: '2px 6px', background: '#fef3c7', color: '#92400e', borderRadius: '4px', fontSize: '10px', marginRight: '4px' }}>
                                  {m}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: '#9ca3af' }}>None</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: LAYERED MULE CHAIN (L1, L2, L3) */}
          {activeTab === 'layers' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
              {/* L1 Collector Mules */}
              <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '2px solid #ef4444', paddingBottom: '8px' }}>
                  <span style={{ width: '12px', height: '12px', backgroundColor: '#ef4444', borderRadius: '50%' }} />
                  <h3 style={{ margin: 0 }}>Layer 1: Collector Mules ({l1Nodes.length})</h3>
                </div>
                <p style={{ fontSize: '12px', color: '#6b7280', margin: '8px 0' }}>
                  Direct recipients of victim funds. Collect large inflows before splitting.
                </p>
                <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
                  {l1Nodes.map((n) => (
                    <div key={n.id} style={{ padding: '8px', borderBottom: '1px solid #f3f4f6', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <b>{n.id}</b>
                        <span style={{ color: '#ef4444', fontWeight: 'bold' }}>Risk: {n.risk || 0}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Bank: {n.bank || '—'} · Role: {n.role}</div>
                      <button
                        className="secondary"
                        style={{ padding: '2px 6px', fontSize: '10px', marginTop: '4px' }}
                        onClick={() => {
                          set({ isolatedNode: n.id, selectedNode: n });
                          setActiveTab('graph');
                        }}
                      >
                        Isolate Subgraph →
                      </button>
                    </div>
                  ))}
                  {!l1Nodes.length && <div className="empty">No L1 accounts detected.</div>}
                </div>
              </div>

              {/* L2 Distributor Mules */}
              <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '2px solid #f59e0b', paddingBottom: '8px' }}>
                  <span style={{ width: '12px', height: '12px', backgroundColor: '#f59e0b', borderRadius: '50%' }} />
                  <h3 style={{ margin: 0 }}>Layer 2: Distributor Mules ({l2Nodes.length})</h3>
                </div>
                <p style={{ fontSize: '12px', color: '#6b7280', margin: '8px 0' }}>
                  High fan-out pass-through accounts splitting funds across multiple channels.
                </p>
                <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
                  {l2Nodes.map((n) => (
                    <div key={n.id} style={{ padding: '8px', borderBottom: '1px solid #f3f4f6', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <b>{n.id}</b>
                        <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>Risk: {n.risk || 0}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Bank: {n.bank || '—'} · Role: {n.role}</div>
                      <button
                        className="secondary"
                        style={{ padding: '2px 6px', fontSize: '10px', marginTop: '4px' }}
                        onClick={() => {
                          set({ isolatedNode: n.id, selectedNode: n });
                          setActiveTab('graph');
                        }}
                      >
                        Isolate Subgraph →
                      </button>
                    </div>
                  ))}
                  {!l2Nodes.length && <div className="empty">No L2 accounts detected.</div>}
                </div>
              </div>

              {/* L3 Terminal Cash-Out */}
              <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '2px solid #8b5cf6', paddingBottom: '8px' }}>
                  <span style={{ width: '12px', height: '12px', backgroundColor: '#8b5cf6', borderRadius: '50%' }} />
                  <h3 style={{ margin: 0 }}>Layer 3: Terminal Cash-Out ({l3Nodes.length})</h3>
                </div>
                <p style={{ fontSize: '12px', color: '#6b7280', margin: '8px 0' }}>
                  Exit nodes: Crypto P2P, foreign IPs, payment wallets, or ATM cash-outs.
                </p>
                <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
                  {l3Nodes.map((n) => (
                    <div key={n.id} style={{ padding: '8px', borderBottom: '1px solid #f3f4f6', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <b>{n.id}</b>
                        <span style={{ color: '#8b5cf6', fontWeight: 'bold' }}>Risk: {n.risk || 0}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Bank: {n.bank || '—'} · Role: {n.role}</div>
                      <button
                        className="secondary"
                        style={{ padding: '2px 6px', fontSize: '10px', marginTop: '4px' }}
                        onClick={() => {
                          set({ isolatedNode: n.id, selectedNode: n });
                          setActiveTab('graph');
                        }}
                      >
                        Isolate Subgraph →
                      </button>
                    </div>
                  ))}
                  {!l3Nodes.length && <div className="empty">No L3 accounts detected.</div>}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: TOPOLOGIES & RISK ANALYSIS */}
          {activeTab === 'topologies' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {/* High-Velocity Pass-Through Panel */}
              <div className="card">
                <h3>⚡ High-Velocity Pass-Through Analysis</h3>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>
                  Nodes dispersing ≥90% of incoming funds within a rapid 15-minute window.
                </p>
                <div style={{ marginTop: '12px', padding: '12px', backgroundColor: '#fef3c7', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <b>STATUS:</b>
                    <span style={{ fontWeight: 'bold', color: '#b45309' }}>ACTIVE MONITORING</span>
                  </div>
                  <div style={{ fontSize: '12px', lineHeight: '1.8' }}>
                    <div><b>Dispersal Window:</b> ≤ 15 minutes (Configured)</div>
                    <div><b>Passthrough Fraction:</b> ≥ 90%</div>
                    <div><b>Min Outgoing Transfers:</b> ≥ 2 counterparties</div>
                  </div>
                </div>
                <h4 style={{ marginTop: '16px' }}>Flagged Pass-Through Nodes in Trace</h4>
                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  {trace.nodes
                    .filter((n) => (n.risk || 0) >= 40)
                    .map((n) => (
                      <div key={n.id} style={{ padding: '6px', borderBottom: '1px solid #f3f4f6', fontSize: '12px', display: 'flex', justifyContent: 'space-between' }}>
                        <span><b>{n.id}</b> ({n.layer})</span>
                        <span style={{ color: '#b45309', fontWeight: 'bold' }}>Risk Score: {n.risk}/100</span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Terminal Cash-Out Indicators Panel */}
              <div className="card">
                <h3>🛑 Terminal Cash-Out Indicators</h3>
                <p style={{ fontSize: '12px', color: '#6b7280' }}>
                  Specific markers derived from underlying transaction and device metadata.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
                  <div style={{ padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#047857', fontWeight: 'bold' }}>✓</span>
                    <div>
                      <b>Crypto / P2P Settlement Narration</b>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Matches regex: crypto, usdt, binance, p2p</div>
                    </div>
                  </div>
                  <div style={{ padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#047857', fontWeight: 'bold' }}>✓</span>
                    <div>
                      <b>Foreign / Proxy IP Detection</b>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Matches prefixes: 185., 194.</div>
                    </div>
                  </div>
                  <div style={{ padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#047857', fontWeight: 'bold' }}>✓</span>
                    <div>
                      <b>Suspicious / Headless Device Profile</b>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Web_Emulator, Linux_Script</div>
                    </div>
                  </div>
                  <div style={{ padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#047857', fontWeight: 'bold' }}>✓</span>
                    <div>
                      <b>Payment Wallet / Gift Card Drains</b>
                      <div style={{ fontSize: '11px', color: '#6b7280' }}>Wallet, Paytm, PhonePe</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: TIMELINE EVENTS */}
          {activeTab === 'timeline' && (
            <div className="card table-card">
              <h3>Minute-Level Chronological Timeline ({trace.timeline?.length || 0} events)</h3>
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Sender</th>
                    <th>Receiver</th>
                    <th>Amount</th>
                    <th>Layer</th>
                    <th>Markers</th>
                  </tr>
                </thead>
                <tbody>
                  {trace.timeline?.map((e: any) => (
                    <tr key={e.id}>
                      <td><time>{e.ts}</time></td>
                      <td><b>{e.from}</b></td>
                      <td><b>{e.to}</b></td>
                      <td>₹{(Number(e.amount) / 100).toLocaleString('en-IN')}</td>
                      <td>
                        <span style={{ padding: '2px 6px', backgroundColor: LAYER_COLORS[`L${e.hop}`] || '#e5e7eb', color: '#fff', borderRadius: '4px', fontSize: '10px' }}>
                          L{e.hop}
                        </span>
                      </td>
                      <td>{e.markers?.join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 5: FIFO ATTRIBUTION & RESIDUALS */}
          {activeTab === 'evidence' && (
            <div className="card table-card">
              <h3>FIFO Flow Attribution and Residual Balances</h3>
              <table>
                <thead>
                  <tr>
                    <th>Transaction ID</th>
                    <th>Sender</th>
                    <th>Receiver</th>
                    <th>Amount</th>
                    <th>Residual (paise)</th>
                    <th>Markers</th>
                  </tr>
                </thead>
                <tbody>
                  {trace.edges.map((e) => (
                    <tr key={e.id}>
                      <td><small>{e.id}</small></td>
                      <td>{e.from}</td>
                      <td>{e.to}</td>
                      <td><b>₹{(Number(e.amount) / 100).toLocaleString('en-IN')}</b></td>
                      <td>₹{(Number(e.residual_paise || 0) / 100).toLocaleString('en-IN')}</td>
                      <td>{e.markers.join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <div className="empty">Enter an account number above to trace the money trail.</div>
      )}

      {/* Save Case Modal */}
      {caseModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="card" style={{ width: '400px', backgroundColor: '#fff' }}>
            <h3>Save Investigation Case</h3>
            <p style={{ fontSize: '12px', color: '#6b7280' }}>
              Creates an immutable case record with cryptographic evidence seal.
            </p>
            <label style={{ display: 'block', margin: '12px 0' }}>
              Victim Account
              <input value={victim} disabled style={{ width: '100%', backgroundColor: '#f3f4f6' }} />
            </label>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button className="secondary" onClick={() => setCaseModalOpen(false)}>Cancel</button>
              <button className="primary" onClick={handleCreateCase}>Create Case</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Cases() {
  const { apiKey, set } = useStore();
  const [rows, setRows] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => {
    setLoading(true);
    api('/api/cases', {}, apiKey)
      .then((x) => setRows(x.cases || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [apiKey]);

  async function openCase(caseId: string) {
    setLoading(true);
    try {
      const res = await api(`/api/cases/${caseId}`, {}, apiKey);
      setSelectedCase(res);
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function generateDoc(caseId: string, kind: 'diary' | 'freeze') {
    setStatus(`Generating ${kind} report…`);
    try {
      const endpoint = kind === 'diary' ? `/api/cases/${caseId}/generate-case-diary` : `/api/cases/${caseId}/generate-freeze`;
      const res = await api(endpoint, { method: 'POST' }, apiKey);
      setStatus(`Generated ${kind}: ${res.pdf}`);
    } catch (e: any) {
      setStatus(e.message);
    }
  }

  return (
    <>
      <div className="intro">
        <div>
          <small>CASE MANAGEMENT</small>
          <h2>Cyber Arc Investigation Cases</h2>
          <p>Locally stored case records preserve graph, timeline, evidence, and document references.</p>
        </div>
      </div>

      <div className="card table-card">
        <table>
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Victim</th>
              <th>Created</th>
              <th>Status</th>
              <th>Risk Score</th>
              <th>Total Traced</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.case_id}>
                <td><b>{r.case_id}</b></td>
                <td>{r.victim_account}</td>
                <td><small>{r.created_at}</small></td>
                <td>
                  <span style={{ padding: '2px 6px', background: '#ecfdf5', color: '#047857', borderRadius: '4px', fontSize: '11px' }}>
                    {r.status}
                  </span>
                </td>
                <td><b>{r.risk} / 100</b></td>
                <td>₹{(Number(r.total_traced || 0) / 100).toLocaleString('en-IN')}</td>
                <td>
                  <button
                    className="secondary"
                    style={{ padding: '4px 8px', fontSize: '11px' }}
                    onClick={() => openCase(r.case_id)}
                  >
                    View Case Dossier →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && !loading && (
          <div className="empty">No local cases yet. Run a victim trace and click "+ Save as Case".</div>
        )}
      </div>

      {/* Case Detail Dossier */}
      {selectedCase && (
        <div className="card" style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Case Dossier: {selectedCase.case_id}</h3>
            <button className="secondary" onClick={() => setSelectedCase(null)}>✕ Close</button>
          </div>

          <div className="stats compact" style={{ margin: '12px 0' }}>
            <div className="stat">
              <small>VICTIM ACCOUNT</small>
              <b>{selectedCase.victim_account}</b>
            </div>
            <div className="stat">
              <small>SUSPECT NODES</small>
              <b>{selectedCase.suspect_accounts?.length || 0}</b>
            </div>
            <div className="stat">
              <small>HOLDING NODES</small>
              <b>{selectedCase.holding_accounts?.length || 0}</b>
            </div>
            <div className="stat">
              <small>EVIDENCE ID</small>
              <b><small>{selectedCase.evidence_ids?.[0] || '—'}</small></b>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', margin: '12px 0' }}>
            <button className="primary" onClick={() => generateDoc(selectedCase.case_id, 'diary')}>
              Generate Case Diary (PDF)
            </button>
            <button className="primary" onClick={() => generateDoc(selectedCase.case_id, 'freeze')}>
              Generate Freeze Requisition (PDF)
            </button>
          </div>
          <span className="status">{status}</span>
        </div>
      )}
    </>
  );
}

function Evidence() {
  const { apiKey, trace, evidence, set } = useStore();
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [generatedReports, setGeneratedReports] = useState<any[]>([]);

  async function report(kind: string) {
    if (!trace) return setStatus('Run a trace first.');
    setLoading(true);
    setStatus(`Generating ${kind}…`);
    try {
      const e = evidence || (await api(`/api/evidence?victim=${trace.nodes[0].id}&max_hops=4`, { method: 'POST' }, apiKey));
      set({ evidence: e });
      const r = await api(`/api/reports/${e.evidence_id}?kind=${kind}`, { method: 'POST' }, apiKey);
      setStatus(`Generated ${kind} successfully!`);
      setGeneratedReports((prev) => [...prev, { kind, ...r }]);
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="intro">
        <div>
          <small>CASE MATERIALS & LEGAL COMPLIANCE</small>
          <h2>Evidence & Reports</h2>
          <p>Seal the money trail, verify SHA-256 cryptographic digests, and generate court-ready legal documents.</p>
        </div>
        <span className="pill">Evidence anchored</span>
      </div>

      <div className="report-grid">
        <section className="card report">
          <h3>Automated Police Case Diary</h3>
          <p>Chronological money trail, positional account layers (L1/L2/L3), risk reasons, FIFO attribution links, and officer notes.</p>
          <button className="secondary" onClick={() => report('case-diary')} disabled={loading}>
            Generate Case Diary (PDF/HTML) →
          </button>
        </section>
        <section className="card report">
          <h3>Automated Bank Freeze Requisition</h3>
          <p>Bank-grouped beneficiary accounts, IFSC routing codes, disputed transactions, and Section 91 CrPC requisition references.</p>
          <button className="secondary" onClick={() => report('freeze')} disabled={loading}>
            Generate Freeze Requisition (PDF/HTML) →
          </button>
        </section>
      </div>

      <div className="card evidence" style={{ marginTop: '16px' }}>
        <b>Evidence Integrity Status</b>
        <p>
          {evidence
            ? `Sealed Evidence ID: ${evidence.evidence_id} · SHA-256 Digest: ${evidence.seal}`
            : 'Run a victim trace first to anchor findings into sealed evidence.'}
        </p>
        <span className="status">{status}</span>

        {generatedReports.length > 0 && (
          <div style={{ marginTop: '16px', borderTop: '1px solid #e5e7eb', paddingTop: '12px' }}>
            <h4>Generated Document Artifacts</h4>
            {generatedReports.map((r, i) => (
              <div key={i} style={{ padding: '8px', backgroundColor: '#f9fafb', borderRadius: '4px', margin: '6px 0', fontSize: '12px' }}>
                <b>{r.kind.toUpperCase()}</b>:
                <div style={{ wordBreak: 'break-all', marginTop: '4px' }}>
                  <span>PDF: <code>{r.pdf}</code></span>
                  <br />
                  <span>HTML: <code>{r.html}</code></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function Benchmarks() {
  const { apiKey } = useStore();
  const [data, setData] = useState<any>({});

  useEffect(() => {
    api('/api/benchmarks', {}, apiKey)
      .then(setData)
      .catch(() => {});
  }, [apiKey]);

  return (
    <>
      <div className="intro">
        <div>
          <small>BENCHMARK ARTIFACTS</small>
          <h2>System Benchmarks</h2>
          <p>Values appear only when a local benchmark result has been saved.</p>
        </div>
      </div>

      <div className="stats compact" style={{ marginBottom: '16px' }}>
        <div className="stat">
          <small>2M INGESTION TARGET</small>
          <b>≤ 60.0 s</b>
          <span>Measured: {data['ingestion_latest.json']?.ingestion_seconds != null ? `${data['ingestion_latest.json'].ingestion_seconds} s` : 'Not measured'}</span>
        </div>
        <div className="stat">
          <small>4-HOP TRACE TARGET</small>
          <b>≤ 2.0 s</b>
          <span>Measured: {data['trace_latest.json']?.average_ms != null ? `${data['trace_latest.json'].average_ms} ms average` : 'Not measured'}</span>
        </div>
        <div className="stat">
          <small>PEAK RAM CONSUMPTION</small>
          <b>≤ 16 GB</b>
          <span>Measured: {data['ingestion_latest.json']?.peak_rss_mb != null ? `${data['ingestion_latest.json'].peak_rss_mb} MB` : 'Not measured'}</span>
        </div>
      </div>

      <div className="card table-card">
        <h3>Benchmark Execution Results (JSON)</h3>
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </div>
    </>
  );
}

export default function App() {
  const { view, darkMode } = useStore();
  return (
    <div className="shell" data-theme={darkMode ? 'dark' : 'light'}>
      <Sidebar />
      <main>
        <Header />
        {view === 'overview' && <Overview />}
        {view === 'datasets' && <Datasets />}
        {view === 'trace' && <TraceView />}
        {view === 'search' && <AccountSearch />}
        {view === 'cases' && <Cases />}
        {view === 'evidence' && <Evidence />}
        {view === 'benchmarks' && <Benchmarks />}
      </main>
    </div>
  );
}

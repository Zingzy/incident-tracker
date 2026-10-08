import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const SEVERITIES = ['SEV1', 'SEV2', 'SEV3', 'SEV4']
const STATUSES = ['open', 'investigating', 'resolved']
const json = { 'Content-Type': 'application/json' }

async function api(path, options) {
  const response = await fetch(`/api${path}`, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.status === 204 ? null : response.json()
}

function clock(value) {
  return new Date(value).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function duration(seconds) {
  if (seconds == null) return 'n/a'
  const s = Math.round(seconds)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
}

function App() {
  const [info, setInfo] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [stats, setStats] = useState(null)
  const [filters, setFilters] = useState({ status: '', severity: '' })
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')

  async function load(id = selected?.id) {
    try {
      const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString()
      const [nextInfo, list, nextStats] = await Promise.all([
        api('/info'),
        api(`/incidents${query ? `?${query}` : ''}`),
        api('/stats'),
      ])
      setInfo(nextInfo)
      setIncidents(list)
      setStats(nextStats)
      setSelected(id ? await api(`/incidents/${id}`).catch(() => null) : null)
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [filters])

  async function create(event) {
    event.preventDefault()
    const form = event.currentTarget
    const data = Object.fromEntries(new FormData(form))
    try {
      const incident = await api('/incidents', { method: 'POST', headers: json, body: JSON.stringify(data) })
      form.reset()
      setFormError('')
      load(incident.id)
    } catch (e) {
      setFormError(e.message)
    }
  }

  async function setStatus(status) {
    await api(`/incidents/${selected.id}/status`, { method: 'POST', headers: json, body: JSON.stringify({ status }) })
    load(selected.id)
  }

  async function addNote(event) {
    event.preventDefault()
    const form = event.currentTarget
    const body = new FormData(form).get('body')
    if (!body.trim()) return
    await api(`/incidents/${selected.id}/notes`, { method: 'POST', headers: json, body: JSON.stringify({ body }) })
    form.reset()
    load(selected.id)
  }

  const unknown = loading || Boolean(error) || !stats

  return (
    <div className="page">
      <header className="top">
        <h1>{info?.site_title ?? 'Incident Tracker'}</h1>
        <dl className="meta">
          <div><dt>env</dt><dd>{info?.environment ?? '...'}</dd></div>
          <div><dt>build</dt><dd>{info?.version?.slice(0, 7) ?? '...'}</dd></div>
        </dl>
      </header>

      {error && (
        <div className="alert" role="alert">
          <b>The API did not answer.</b>
          <span>{error}. Check that the backend and PostgreSQL are running, then reload.</span>
        </div>
      )}

      <section className="stats">
        <Stat label="open" value={unknown ? '...' : stats.open} />
        {SEVERITIES.map((sev) => (
          <Stat key={sev} label={sev.toLowerCase()} value={unknown ? '...' : stats.open_by_severity[sev]} hot={sev === 'SEV1' && stats?.open_by_severity.SEV1 > 0} />
        ))}
        <Stat label="mean time to resolve" value={unknown ? '...' : duration(stats.mean_time_to_resolve_seconds)} />
      </section>

      <div className="grid">
        <section className="panel">
          <form className="create" onSubmit={create}>
            <input name="title" required maxLength={200} placeholder="What is broken?" className="grow" />
            <input name="service" required maxLength={80} placeholder="service" />
            <select name="severity" defaultValue="SEV3">
              {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
            </select>
            <button className="primary" type="submit">Open incident</button>
            {formError && <p className="form-error">{formError}</p>}
          </form>

          <div className="filters">
            <div className="segmented" role="group" aria-label="Status filter">
              {['', ...STATUSES].map((s) => (
                <button key={s || 'all'} className={filters.status === s ? 'on' : ''} onClick={() => setFilters({ ...filters, status: s })}>
                  {s || 'all'}
                </button>
              ))}
            </div>
            <select aria-label="Severity filter" value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
              <option value="">all severities</option>
              {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>

          {loading ? (
            <p className="empty">Loading incidents</p>
          ) : error ? (
            <p className="empty">Incidents could not be loaded.</p>
          ) : incidents.length === 0 ? (
            <p className="empty">No incidents match these filters.</p>
          ) : (
            <ul className="list">
              {incidents.map((i) => (
                <li key={i.id}>
                  <button className={`row ${selected?.id === i.id ? 'active' : ''}`} onClick={() => load(i.id)}>
                    <span className="mono muted">#{i.id}</span>
                    <span className="title">{i.title}</span>
                    <span className="mono muted">{i.service}</span>
                    <span className={`mono sev ${i.severity === 'SEV1' ? 'hot' : ''}`}>{i.severity}</span>
                    <span className="mono muted status">{i.status}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel detail">
          {!selected ? (
            <p className="empty">Select an incident to see its timeline.</p>
          ) : (
            <>
              <div className="detail-head">
                <h2>{selected.title}</h2>
                <p className="mono muted">
                  #{selected.id} · {selected.service} · <span className={selected.severity === 'SEV1' ? 'hot' : ''}>{selected.severity}</span> · {selected.status}
                  {selected.resolved_at && ` · resolved ${clock(selected.resolved_at)}`}
                </p>
              </div>
              <div className="actions">
                {STATUSES.filter((s) => s !== selected.status).map((s) => (
                  <button key={s} className="ghost" onClick={() => setStatus(s)}>
                    {s === 'resolved' ? 'Resolve' : s === 'open' ? 'Reopen' : 'Investigating'}
                  </button>
                ))}
              </div>
              <ol className="timeline">
                {selected.notes.map((n) => (
                  <li key={n.id}>
                    <time className="mono muted">{clock(n.created_at)}</time>
                    <span>{n.body}</span>
                  </li>
                ))}
              </ol>
              <form className="note" onSubmit={addNote}>
                <input name="body" maxLength={2000} placeholder="Add a note to the timeline" className="grow" />
                <button className="ghost" type="submit">Add note</button>
              </form>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

function Stat({ label, value, hot }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong className={hot ? 'hot' : ''}>{value}</strong>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)

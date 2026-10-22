
import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

const API = 'http://127.0.0.1:8000'

type RFQ = {
  id: number
  name: string
  current_lowest_bid?: number | null
  bid_start?: string
  bid_close: string
  forced_close: string
  pickup_date?: string
  status: string
}

type Bid = {
  id: number
  supplier_id: string
  carrier_name: string
  freight: number
  origin_charges: number
  destination_charges: number
  total_price: number
  transit_time: string
  quote_validity: string
  created_at: string
}

type Ranking = {
  rank: number
  supplier_id: string
  carrier_name: string
  total_price: number
}

type Activity = {
  event_type: string
  message: string
  old_close?: string | null
  new_close?: string | null
  created_at: string
}

type RFQDetails = RFQ & {
  config: {
    trigger_window_x: number
    extension_y: number
    trigger_type: string
  }
  bids: Bid[]
  ranking: Ranking[]
  activity_log: Activity[]
}

const money = (value: number | null | undefined) => {
  if (value == null) return 'No bids yet'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value)
}

const dateTime = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('en-IN')
}

function App() {
  const [rfqs, setRfqs] = useState<RFQ[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [currentPage, setCurrentPage] = useState<'list' | 'details'>('list')
  const [details, setDetails] = useState<RFQDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [showBid, setShowBid] = useState(false)

  const [rfqForm, setRfqForm] = useState({
    name: '',
    bid_start: '',
    bid_close: '',
    forced_close: '',
    pickup_date: '',
    trigger_window_x: '10',
    extension_y: '5',
    trigger_type: 'BID_RECEIVED',
  })

  const [bidForm, setBidForm] = useState({
    supplier_id: '',
    carrier_name: '',
    freight: '',
    origin_charges: '0',
    destination_charges: '0',
    transit_time: '',
    quote_validity: '',
  })

  const request = async (path: string, options?: RequestInit) => {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      throw new Error(data.detail || `Request failed (${response.status})`)
    }

    return data
  }

  const loadRFQs = useCallback(async () => {
    try {
      const data = await request('/rfqs')
      setRfqs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load RFQs')
    } finally {
      setLoading(false)
    }
  }, [])

  
const loadDetails = useCallback(async (id: number) => {
  setDetailsLoading(true)
  setError('')

  try {
    const data = await request(`/rfqs/${id}`)
    console.log('RFQ DETAILS RECEIVED:', data)
    setDetails(data)
  } catch (err) {
    console.error('RFQ DETAILS ERROR:', err)
    setError(
      err instanceof Error ? err.message : 'Unable to load RFQ details',
    )
  } finally {
    setDetailsLoading(false)
  }
}, [])


  useEffect(() => {
    void loadRFQs()
  }, [loadRFQs])

  useEffect(() => {
    if (selectedId !== null) {
      void loadDetails(selectedId)
    } else {
      setDetails(null)
    }
  }, [selectedId, loadDetails])

  const selectRFQ = (id: number) => {
    setError('')
    setNotice('')
    setShowBid(false)
    setSelectedId(id)
    setCurrentPage('details')
  }

  const createRFQ = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')

    try {
      const data = await request('/rfqs', {
        method: 'POST',
        body: JSON.stringify({
          name: rfqForm.name.trim(),
          bid_start: new Date(rfqForm.bid_start).toISOString(),
          bid_close: new Date(rfqForm.bid_close).toISOString(),
          forced_close: new Date(rfqForm.forced_close).toISOString(),
          pickup_date: rfqForm.pickup_date,
          config: {
            trigger_window_x: Number(rfqForm.trigger_window_x),
            extension_y: Number(rfqForm.extension_y),
            trigger_type: rfqForm.trigger_type,
          },
        }),
      })

      setShowCreate(false)
      setNotice(`RFQ #${data.id} created successfully.`)
      setRfqForm({
        name: '',
        bid_start: '',
        bid_close: '',
        forced_close: '',
        pickup_date: '',
        trigger_window_x: '10',
        extension_y: '5',
        trigger_type: 'BID_RECEIVED',
      })

      await loadRFQs()
      setSelectedId(data.id)
      setCurrentPage('details')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create RFQ')
    } finally {
      setBusy(false)
    }
  }

  const submitBid = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (selectedId === null) return

    setBusy(true)
    setError('')
    setNotice('')

    try {
      const data = await request(`/rfqs/${selectedId}/bids`, {
        method: 'POST',
        body: JSON.stringify({
          supplier_id: bidForm.supplier_id.trim(),
          carrier_name: bidForm.carrier_name.trim(),
          freight: Number(bidForm.freight),
          origin_charges: Number(bidForm.origin_charges),
          destination_charges: Number(bidForm.destination_charges),
          transit_time: bidForm.transit_time.trim(),
          quote_validity: bidForm.quote_validity,
        }),
      })

      setNotice(
        `Bid submitted! Total: ${money(data.total_price)}. Rank: ${data.rank ?? '—'}. ${
          data.extension_triggered ? 'Auction extended.' : 'No auction extension.'
        }`,
      )
      setShowBid(false)
      setBidForm({
        supplier_id: '',
        carrier_name: '',
        freight: '',
        origin_charges: '0',
        destination_charges: '0',
        transit_time: '',
        quote_validity: '',
      })

      await loadDetails(selectedId)
      await loadRFQs()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit bid')
    } finally {
      setBusy(false)
    }
  }

  const statusClass = (status: string) =>
    status.toLowerCase().replaceAll('_', '-')

  const activeCount = rfqs.filter((rfq) => rfq.status === 'ACTIVE').length

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">B</div>
          <div>
            <strong>bidflow</strong>
            <span>AUCTION PLATFORM</span>
          </div>
        </div>

        <div className="side-label">WORKSPACE</div>
        <button
          className="nav-item active"
          onClick={() => {
            setCurrentPage('list')
            setSelectedId(null)
            setShowCreate(false)
            setShowBid(false)
          }}
        >
          <span>▦</span> RFQ Auctions
        </button>

        <div className="sidebar-bottom">
          <div className="avatar">U</div>
          <div>
            <strong>Workspace Admin</strong>
            <span>Procurement team</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>British Auctions</strong>
          </div>
          <div className="connection">
            <span className="online-dot" /> API workspace
          </div>
        </header>

        <section className="page-heading">
          <div>
            <div className="eyebrow">PROCUREMENT · LIVE WORKSPACE</div>
            <h1>{currentPage === 'details' ? 'RFQ Auction Details' : 'British Auction Dashboard'}</h1>
            <p>{currentPage === 'details' ? 'Review auction settings, supplier bids and ranking activity.' : 'Manage freight RFQs, supplier bids and auction rankings.'}</p>
          </div>
          {currentPage === 'list' && <button
            className="primary-button"
            onClick={() => {
              setError('')
              setNotice('')
              setShowCreate(!showCreate)
              setShowBid(false)
            }}
          >
            ＋ Create RFQ
          </button>}
        </section>

        {error && (
          <div className="alert error-alert">
            <span>{error}</span>
            <button onClick={() => setError('')}>×</button>
          </div>
        )}

        {notice && (
          <div className="alert success-alert">
            <span>{notice}</span>
            <button onClick={() => setNotice('')}>×</button>
          </div>
        )}

        {currentPage === 'list' && <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-top">
              <span>Total RFQs</span>
              <span className="stat-icon purple">▤</span>
            </div>
            <strong>{rfqs.length}</strong>
            <small>All procurement events</small>
          </div>
          <div className="stat-card">
            <div className="stat-top">
              <span>Active auctions</span>
              <span className="stat-icon green">↗</span>
            </div>
            <strong>{activeCount}</strong>
            <small>Currently accepting bids</small>
          </div>
          <div className="stat-card">
            <div className="stat-top">
              <span>Selected RFQ bids</span>
              <span className="stat-icon orange">⇅</span>
            </div>
            <strong>{details?.bids.length ?? 0}</strong>
            <small>{details ? `RFQ #${details.id}` : 'Select an RFQ'}</small>
          </div>
        </section>}

        {currentPage === 'list' && showCreate && (
          <section className="panel form-panel">
            <div className="panel-heading">
              <div>
                <h2>Create a freight RFQ</h2>
                <p>Configure the auction schedule and extension rules.</p>
              </div>
              <button className="icon-button" onClick={() => setShowCreate(false)}>
                ×
              </button>
            </div>

            <form onSubmit={createRFQ}>
              <div className="form-grid">
                <label className="field full-field">
                  RFQ name
                  <input
                    required
                    maxLength={150}
                    value={rfqForm.name}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, name: e.target.value })
                    }
                    placeholder="Hyderabad to Bangalore freight"
                  />
                </label>
                <label className="field">
                  Bid start
                  <input
                    required
                    type="datetime-local"
                    value={rfqForm.bid_start}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, bid_start: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Initial bid close
                  <input
                    required
                    type="datetime-local"
                    value={rfqForm.bid_close}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, bid_close: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Forced close
                  <input
                    required
                    type="datetime-local"
                    value={rfqForm.forced_close}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, forced_close: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Pickup date
                  <input
                    required
                    type="date"
                    value={rfqForm.pickup_date}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, pickup_date: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Trigger window X (minutes)
                  <input
                    required
                    min="1"
                    type="number"
                    value={rfqForm.trigger_window_x}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, trigger_window_x: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Extension Y (minutes)
                  <input
                    required
                    min="1"
                    type="number"
                    value={rfqForm.extension_y}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, extension_y: e.target.value })
                    }
                  />
                </label>
                <label className="field full-field">
                  Extension trigger
                  <select
                    value={rfqForm.trigger_type}
                    onChange={(e) =>
                      setRfqForm({ ...rfqForm, trigger_type: e.target.value })
                    }
                  >
                    <option value="BID_RECEIVED">Any bid received</option>
                    <option value="ANY_RANK_CHANGE">Any ranking change</option>
                    <option value="L1_CHANGE">L1 supplier changes</option>
                  </select>
                </label>
              </div>
              <div className="form-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </button>
                <button className="primary-button" disabled={busy}>
                  {busy ? 'Creating…' : 'Create auction'}
                </button>
              </div>
            </form>
          </section>
        )}

        {currentPage === 'list' && <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>RFQ auctions</h2>
              <p>Select an auction to inspect bids and rankings.</p>
            </div>
            <button className="secondary-button" onClick={() => void loadRFQs()}>
              ↻ Refresh
            </button>
          </div>

          {loading ? (
            <div className="empty-state">Loading RFQs…</div>
          ) : rfqs.length === 0 ? (
            <div className="empty-state">
              <strong>No RFQs yet</strong>
              <p>Create your first RFQ to get started.</p>
            </div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>RFQ / Auction</th>
                    <th>Status</th>
                    <th>Lowest bid</th>
                    <th>Bid closes</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {rfqs.map((rfq) => (
                    <tr
                      key={rfq.id}
                      className={selectedId === rfq.id ? 'selected-row' : ''}
                    >
                      <td>
                        <button
                          className="rfq-name"
                          onClick={() => selectRFQ(rfq.id)}
                        >
                          {rfq.name}
                        </button>
                        <span className="subtext">RFQ-{rfq.id}</span>
                      </td>
                      <td>
                        <span className={`status-pill ${statusClass(rfq.status)}`}>
                          <span className="status-dot" />
                          {rfq.status.replaceAll('_', ' ')}
                        </span>
                      </td>
                      <td className="price-cell">{money(rfq.current_lowest_bid)}</td>
                      <td>{dateTime(rfq.bid_close)}</td>
                      <td>
                        <button
                          className="text-button"
                          onClick={() => selectRFQ(rfq.id)}
                        >
                          View details →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>}

        {currentPage === 'details' && detailsLoading && (
          <section className="panel">
            <div className="empty-state">Loading RFQ details…</div>
          </section>
        )}

        {currentPage === 'details' && !detailsLoading && !details && (
          <section className="panel">
            <div className="empty-state">
              <strong>RFQ details are not available.</strong>
              <p>Return to the auction list and select an RFQ again.</p>
              <button className="secondary-button" onClick={() => setCurrentPage('list')}>
                ← Back to RFQ Auctions
              </button>
            </div>
          </section>
        )}

        {currentPage === 'details' && details && !detailsLoading && (
          <>
            <section className="panel details-panel">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">RFQ-{details.id} · AUCTION DETAILS</div>
                  <h2>{details.name}</h2>
                  <p>Pickup date: {details.pickup_date ?? '—'}</p>
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      setCurrentPage('list')
                      setShowBid(false)
                      setError('')
                      setNotice('')
                    }}
                  >
                    ← Back to RFQ Auctions
                  </button>
                  <button
                    className="primary-button"
                    disabled={details.status !== 'ACTIVE'}
                  onClick={() => {
                    setError('')
                    setNotice('')
                    setShowBid(!showBid)
                    setShowCreate(false)
                  }}
                >
                    ＋ Submit bid
                  </button>
                </div>
              </div>

              <div className="timeline-grid">
                <div className="timeline-item">
                  <span>Bid starts</span>
                  <strong>{dateTime(details.bid_start)}</strong>
                </div>
                <div className="timeline-item">
                  <span>Current close</span>
                  <strong>{dateTime(details.bid_close)}</strong>
                </div>
                <div className="timeline-item">
                  <span>Forced close cap</span>
                  <strong>{dateTime(details.forced_close)}</strong>
                </div>
                <div className="timeline-item">
                  <span>Extension rule</span>
                  <strong>
                    +{details.config.extension_y} min / last{' '}
                    {details.config.trigger_window_x} min
                  </strong>
                  <small>{details.config.trigger_type.replaceAll('_', ' ')}</small>
                </div>
              </div>

              {showBid && (
                <form className="bid-form" onSubmit={submitBid}>
                  <h3>Submit supplier bid</h3>
                  <div className="form-grid">
                    <label className="field">
                      Supplier ID
                      <input
                        required
                        value={bidForm.supplier_id}
                        onChange={(e) =>
                          setBidForm({ ...bidForm, supplier_id: e.target.value })
                        }
                        placeholder="SUP-001"
                      />
                    </label>
                    <label className="field">
                      Carrier name
                      <input
                        required
                        value={bidForm.carrier_name}
                        onChange={(e) =>
                          setBidForm({ ...bidForm, carrier_name: e.target.value })
                        }
                        placeholder="ABC Logistics"
                      />
                    </label>
                    <label className="field">
                      Freight (₹)
                      <input
                        required
                        min="0"
                        step="0.01"
                        type="number"
                        value={bidForm.freight}
                        onChange={(e) =>
                          setBidForm({ ...bidForm, freight: e.target.value })
                        }
                      />
                    </label>
                    <label className="field">
                      Origin charges (₹)
                      <input
                        required
                        min="0"
                        step="0.01"
                        type="number"
                        value={bidForm.origin_charges}
                        onChange={(e) =>
                          setBidForm({ ...bidForm, origin_charges: e.target.value })
                        }
                      />
                    </label>
                    <label className="field">
                      Destination charges (₹)
                      <input
                        required
                        min="0"
                        step="0.01"
                        type="number"
                        value={bidForm.destination_charges}
                        onChange={(e) =>
                          setBidForm({
                            ...bidForm,
                            destination_charges: e.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      Transit time
                      <input
                        required
                        value={bidForm.transit_time}
                        onChange={(e) =>
                          setBidForm({ ...bidForm, transit_time: e.target.value })
                        }
                        placeholder="4 days"
                      />
                    </label>
                    <label className="field">
                      Quote validity
                      <input
                        required
                        type="date"
                        value={bidForm.quote_validity}
                        onChange={(e) =>
                          setBidForm({ ...bidForm, quote_validity: e.target.value })
                        }
                      />
                    </label>
                  </div>
                  <div className="form-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => setShowBid(false)}
                    >
                      Cancel
                    </button>
                    <button className="primary-button" disabled={busy}>
                      {busy ? 'Submitting…' : 'Submit bid'}
                    </button>
                  </div>
                </form>
              )}
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Supplier leaderboard</h2>
                  <p>Latest bid from each supplier, lowest total price first.</p>
                </div>
                <span className="count-badge">{details.ranking.length} suppliers</span>
              </div>

              {details.ranking.length === 0 ? (
                <div className="empty-state">
                  <strong>No supplier bids yet</strong>
                  <p>Rankings will appear after the first valid bid.</p>
                </div>
              ) : (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Supplier</th>
                        <th>Total price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {details.ranking.map((item) => (
                        <tr key={item.supplier_id}>
                          <td>
                            <span className={`rank-badge rank-${item.rank}`}>
                              {item.rank === 1 ? '♛ L1' : `#${item.rank}`}
                            </span>
                          </td>
                          <td>
                            <strong>{item.carrier_name}</strong>
                            <span className="subtext">{item.supplier_id}</span>
                          </td>
                          <td className="price-cell">{money(item.total_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Bid history</h2>
                  <p>All submitted bids sorted by total price.</p>
                </div>
              </div>
              {details.bids.length === 0 ? (
                <div className="empty-state">No bids recorded for this RFQ.</div>
              ) : (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Carrier</th>
                        <th>Supplier ID</th>
                        <th>Freight</th>
                        <th>Origin</th>
                        <th>Destination</th>
                        <th>Total</th>
                        <th>Submitted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {details.bids.map((bid) => (
                        <tr key={bid.id}>
                          <td>{bid.carrier_name}</td>
                          <td>{bid.supplier_id}</td>
                          <td>{money(bid.freight)}</td>
                          <td>{money(bid.origin_charges)}</td>
                          <td>{money(bid.destination_charges)}</td>
                          <td className="price-cell">{money(bid.total_price)}</td>
                          <td>{dateTime(bid.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Auction activity</h2>
                  <p>Bid submissions and auction extension events.</p>
                </div>
              </div>
              {details.activity_log.length === 0 ? (
                <div className="empty-state">No activity recorded yet.</div>
              ) : (
                <div className="activity-list">
                  {details.activity_log.map((activity, index) => (
                    <div
                      className="activity-item"
                      key={`${activity.created_at}-${index}`}
                    >
                      <div className="activity-marker">
                        {activity.event_type === 'AUCTION_EXTENDED' ? '↗' : '₹'}
                      </div>
                      <div className="activity-content">
                        <strong>{activity.event_type.replaceAll('_', ' ')}</strong>
                        <p>{activity.message}</p>
                        {activity.new_close && (
                          <small>
                            Close moved from {dateTime(activity.old_close)} to{' '}
                            {dateTime(activity.new_close)}
                          </small>
                        )}
                      </div>
                      <time>{dateTime(activity.created_at)}</time>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        <footer className="footer">
          <span>bidflow · British Auction RFQ System</span>
          <span>FastAPI · React · SQLite</span>
        </footer>
      </main>
    </div>
  )
}

export default App

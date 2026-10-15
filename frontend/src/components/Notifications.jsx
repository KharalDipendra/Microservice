import React, { useEffect, useState } from 'react'
import { api } from '../api'

// Shows the mock "emails" held by the notification service (/api/notifications)
export default function Notifications({ onError }) {
  const [notes, setNotes] = useState([])
  const load = () => api('/notifications').then(setNotes).catch(onError)
  useEffect(() => { load() }, [])

  return (
    <>
      <div className="row">
        <h2>Sent Notifications ({notes.length})</h2>
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>
      {notes.length === 0 && <p>No notifications yet. Submit some feedback to trigger one.</p>}
      <div className="grid-gap">
        {notes.map(n => (
          <div key={n.id} className="grid-row">
            <div>
              <div className="title">{n.subject}</div>
              <div className="muted">To: {n.to} · {new Date(n.sent_at).toLocaleString()}</div>
              <div>{n.message}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

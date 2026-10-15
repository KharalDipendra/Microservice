import React, { useState } from 'react'
import './index.css'
import Students from './components/Students'
import Courses from './components/Courses'
import Feedback from './components/Feedback'
import Notifications from './components/Notifications'

const TABS = { Students, Courses, Feedback, Notifications }

export default function App() {
  const [tab, setTab] = useState('Students')
  const [error, setError] = useState('')
  const Page = TABS[tab]

  return (
    // Clicking any button starts a new action, so clear the old error message first
    <div className="container" onClickCapture={e => e.target.tagName === 'BUTTON' && setError('')}>
      <h1>Student Services Dashboard</h1>
      <p>Osborne.AI prototype. Each tab talks to its own microservice through the API gateway.</p>

      <nav className="tabs">
        {Object.keys(TABS).map(name => (
          <button key={name} className={name === tab ? 'tab active' : 'tab'} onClick={() => { setTab(name); setError('') }}>
            {name}
          </button>
        ))}
      </nav>

      {error && <div className="error" onClick={() => setError('')}>{error} (click to dismiss)</div>}

      {/* key={tab} remounts the page so it reloads fresh data each time it is opened */}
      <Page key={tab} onError={e => setError(e.message)} />
    </div>
  )
}

import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api'

// Talks to the student-profile service via /api/students
export default function Students({ onError }) {
  const [students, setStudents] = useState([])
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [search, setSearch] = useState('')
  const [attDate, setAttDate] = useState('')
  const [attStatus, setAttStatus] = useState('Present')

  const load = () => api('/students').then(setStudents).catch(onError)
  useEffect(() => { load() }, [])

  const addStudent = async () => {
    if (!name || !email) return onError(new Error('Name and email are required'))
    try {
      await api('/students', { method: 'POST', body: { name, email } })
      setName(''); setEmail('')
      load()
    } catch (e) { onError(e) }
  }

  const deleteStudent = (id) => api(`/students/${id}`, { method: 'DELETE' }).then(load).catch(onError)

  const addAttendance = async (id) => {
    if (!attDate) return onError(new Error('Pick a date first'))
    try {
      await api(`/students/${id}/attendance`, { method: 'POST', body: { date: attDate, status: attStatus } })
      setAttDate('')
      load()
    } catch (e) { onError(e) }
  }

  const filtered = useMemo(() => students.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.email.toLowerCase().includes(search.toLowerCase())
  ), [students, search])

  return (
    <>
      <section className="grid-2">
        <div className="card">
          <h2>Add Student</h2>
          <input placeholder="Full name" value={name} onChange={e => setName(e.target.value)} />
          <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <button className="btn-primary" onClick={addStudent}>Add</button>
        </div>
        <div className="card">
          <h2>Search</h2>
          <input placeholder="Search by name or email" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </section>

      <h2>Students ({filtered.length})</h2>
      <div className="grid-gap">
        {filtered.map(s => (
          <div key={s.id} className="grid-row">
            <div>
              <div className="title">#{s.id} {s.name}</div>
              <div className="muted">{s.email}</div>
              <details>
                <summary>Attendance ({(s.attendance || []).length})</summary>
                <ul>
                  {(s.attendance || []).map((a, i) => <li key={i}>{a.date} – {a.status}</li>)}
                </ul>
              </details>
            </div>
            <div className="justify-end">
              <div className="row">
                <input type="date" value={attDate} onChange={e => setAttDate(e.target.value)} />
                <select value={attStatus} onChange={e => setAttStatus(e.target.value)}>
                  <option>Present</option>
                  <option>Absent</option>
                  <option>Late</option>
                  <option>Excused</option>
                </select>
                <button className="btn-secondary" onClick={() => addAttendance(s.id)}>Record</button>
              </div>
              <button className="btn-danger" onClick={() => deleteStudent(s.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

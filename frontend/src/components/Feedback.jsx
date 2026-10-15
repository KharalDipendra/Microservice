import React, { useEffect, useState } from 'react'
import { api } from '../api'

// Submits feedback via /api/feedback. The feedback service itself checks the
// student and course exist and triggers the notification service.
export default function Feedback({ onError }) {
  const [students, setStudents] = useState([])
  const [courses, setCourses] = useState([])
  const [feedback, setFeedback] = useState([])
  const [form, setForm] = useState({ student_id: '', course_id: '', rating: 5, comment: '' })
  const [result, setResult] = useState('')

  const load = () => api('/feedback').then(setFeedback).catch(onError)
  useEffect(() => {
    api('/students').then(setStudents).catch(onError)
    api('/courses').then(setCourses).catch(onError)
    load()
  }, [])

  const set = field => e => setForm({ ...form, [field]: e.target.value })
  const studentName = id => students.find(s => s.id === id)?.name || `Student #${id}`
  const courseCode = id => courses.find(c => c.id === id)?.code || `Course #${id}`

  const submit = async () => {
    try {
      const saved = await api('/feedback', { method: 'POST', body: form })
      setResult(saved.notification_sent
        ? `Feedback #${saved.id} saved and confirmation email sent.`
        : `Feedback #${saved.id} saved. The notification service is unavailable, so the email is queued and will be sent automatically when it is back.`)
      setForm({ ...form, comment: '' })
      load()
    } catch (e) { setResult(''); onError(e) }
  }

  return (
    <>
      <div className="card">
        <h2>Submit Feedback</h2>
        <div className="row wrap">
          <select value={form.student_id} onChange={set('student_id')}>
            <option value="">Select student…</option>
            {students.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select value={form.course_id} onChange={set('course_id')}>
            <option value="">Select course…</option>
            {courses.map(c => <option key={c.id} value={c.id}>{c.code} – {c.title}</option>)}
          </select>
          <select value={form.rating} onChange={set('rating')}>
            {[5, 4, 3, 2, 1].map(n => <option key={n} value={n}>{n} ★</option>)}
          </select>
        </div>
        <textarea placeholder="Comment (optional)" value={form.comment} onChange={set('comment')} />
        <button className="btn-primary" onClick={submit}>Submit</button>
        {result && <p className="success">{result}</p>}
      </div>

      <h2>Recent Feedback ({feedback.length})</h2>
      <div className="grid-gap">
        {feedback.map(f => (
          <div key={f.id} className="grid-row">
            <div>
              <div className="title">{courseCode(f.course_id)} · {'★'.repeat(f.rating)}{'☆'.repeat(5 - f.rating)}</div>
              <div className="muted">
                {studentName(f.student_id)} · {new Date(f.created_at).toLocaleString()} · {f.notification_sent ? 'email sent' : 'email queued, will retry'}
              </div>
              {f.comment && <div>{f.comment}</div>}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

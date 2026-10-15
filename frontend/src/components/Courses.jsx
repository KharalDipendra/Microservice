import React, { useEffect, useState } from 'react'
import { api } from '../api'

const EMPTY = { code: '', title: '', credits: 15, semester: '', lecturer: '' }

// Talks to course-catalogue (/api/courses) and shows ratings from feedback (/api/feedback/summary)
export default function Courses({ onError }) {
  const [courses, setCourses] = useState([])
  const [ratings, setRatings] = useState({})
  const [form, setForm] = useState(EMPTY)

  const load = () => {
    api('/courses').then(setCourses).catch(onError)
    api('/feedback/summary')
      .then(rows => setRatings(Object.fromEntries(rows.map(r => [r.course_id, r]))))
      .catch(onError)
  }
  useEffect(() => { load() }, [])

  const set = field => e => setForm({ ...form, [field]: e.target.value })

  const addCourse = async () => {
    try {
      await api('/courses', { method: 'POST', body: { ...form, credits: Number(form.credits) } })
      setForm(EMPTY)
      load()
    } catch (e) { onError(e) }
  }

  const deleteCourse = id => api(`/courses/${id}`, { method: 'DELETE' }).then(load).catch(onError)

  return (
    <>
      <div className="card">
        <h2>Add Course</h2>
        <div className="row wrap">
          <input placeholder="Code (e.g. INFS605)" value={form.code} onChange={set('code')} />
          <input placeholder="Title" value={form.title} onChange={set('title')} />
          <input type="number" min="1" placeholder="Credits" value={form.credits} onChange={set('credits')} />
          <input placeholder="Semester" value={form.semester} onChange={set('semester')} />
          <input placeholder="Lecturer" value={form.lecturer} onChange={set('lecturer')} />
          <button className="btn-primary" onClick={addCourse}>Add</button>
        </div>
      </div>

      <h2>Courses ({courses.length})</h2>
      <div className="grid-gap">
        {courses.map(c => {
          const r = ratings[c.id]
          return (
            <div key={c.id} className="grid-row">
              <div>
                <div className="title">{c.code} – {c.title}</div>
                <div className="muted">
                  {c.credits} credits · {c.semester || 'TBC'} · {c.lecturer || 'TBC'}
                </div>
                <div className="muted">
                  {r ? `★ ${r.average_rating} / 5 from ${r.count} review(s)` : 'No feedback yet'}
                </div>
              </div>
              <button className="btn-danger" onClick={() => deleteCourse(c.id)}>Delete</button>
            </div>
          )
        })}
      </div>
    </>
  )
}

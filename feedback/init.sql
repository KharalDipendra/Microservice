-- Schema for feedback-db (owned only by the feedback service).
-- student_id / course_id refer to records in OTHER services' databases, so there are
-- no foreign keys here: the feedback service validates them over HTTP instead.
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- One feedback per student per course. This also makes a repeated/double-clicked
    -- submission safe: the second one is rejected instead of creating a duplicate.
    UNIQUE (student_id, course_id)
);

-- Outbox: confirmation emails waiting to be delivered by the notification service.
-- A row is written in the SAME transaction as the feedback, so an email can never be
-- "forgotten". sent_at stays NULL until the notification service accepts it; a
-- background job in the feedback service retries unsent rows.
CREATE TABLE IF NOT EXISTS notification_outbox (
    id SERIAL PRIMARY KEY,
    feedback_id INTEGER NOT NULL REFERENCES feedback(id) ON DELETE CASCADE,
    recipient VARCHAR(100) NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ
);

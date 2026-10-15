-- Schema + seed data for course-db (owned only by course-catalogue)
CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    credits INTEGER NOT NULL DEFAULT 15 CHECK (credits > 0),
    semester VARCHAR(20),
    lecturer VARCHAR(100)
);

INSERT INTO courses (code, title, credits, semester, lecturer) VALUES
('INFS605', 'Microservices', 15, 'S2 2026', 'Dr S. Walker'),
('COMP503', 'Programming 2', 15, 'S1 2026', 'Dr A. Smith'),
('INFS602', 'Database Design', 15, 'S1 2026', 'Dr K. Lee'),
('COMP610', 'Software Development Practice', 15, 'S2 2026', 'Dr M. Patel'),
('INFS603', 'Cloud Computing', 15, 'S2 2026', 'Dr R. Ngata');

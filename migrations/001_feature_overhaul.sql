-- SurveillX Feature Overhaul Migration
-- Safe to run multiple times (IF NOT EXISTS / IF NOT EXISTS checks)

-- 1. Student face photos table
CREATE TABLE IF NOT EXISTS student_faces (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    photo_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_student_faces_student_id ON student_faces(student_id);

-- 2. Alert enhancements: status, resolved_at, snapshot_path
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='alerts_logs' AND column_name='status') THEN
        ALTER TABLE alerts_logs ADD COLUMN status TEXT DEFAULT 'unresolved';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='alerts_logs' AND column_name='resolved_at') THEN
        ALTER TABLE alerts_logs ADD COLUMN resolved_at TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='alerts_logs' AND column_name='snapshot_path') THEN
        ALTER TABLE alerts_logs ADD COLUMN snapshot_path TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='alerts_logs' AND column_name='student_id') THEN
        ALTER TABLE alerts_logs ADD COLUMN student_id INTEGER REFERENCES students(id);
    END IF;
END $$;

-- 3. Manual attendance overrides
CREATE TABLE IF NOT EXISTS attendance_manual (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'present',
    note TEXT,
    marked_by TEXT DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_attendance_manual_student_date ON attendance_manual(student_id, date);

-- 4. Notification settings
CREATE TABLE IF NOT EXISTS notification_settings (
    id SERIAL PRIMARY KEY,
    email TEXT,
    notify_high BOOLEAN DEFAULT TRUE,
    notify_medium BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default settings row if empty
INSERT INTO notification_settings (email, notify_high, notify_medium)
SELECT '', TRUE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM notification_settings);

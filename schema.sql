-- Schema for Student Attendance System

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255), -- legacy plaintext (will be phased out)
  password_hash VARCHAR(255),
  fullname VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(30),
  role VARCHAR(20) NOT NULL DEFAULT 'lecturer', -- 'admin' | 'lecturer'
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Classes
CREATE TABLE IF NOT EXISTS classes (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL
);

-- Students
CREATE TABLE IF NOT EXISTS students (
  id SERIAL PRIMARY KEY,
  student_code VARCHAR(50) UNIQUE,
  fullname VARCHAR(255) NOT NULL,
  class_id INTEGER,
  email VARCHAR(255),
  phone VARCHAR(30),
  face_label VARCHAR(255), -- key mapping to labels.json dataset folder/name
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_students_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
);

-- Subjects
CREATE TABLE IF NOT EXISTS subjects (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL
);

-- Map: class <-> subject
CREATE TABLE IF NOT EXISTS class_subjects (
  id SERIAL PRIMARY KEY,
  class_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  UNIQUE (class_id, subject_id),
  CONSTRAINT fk_cs_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  CONSTRAINT fk_cs_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Map: student <-> subject (enrollment per subject)
CREATE TABLE IF NOT EXISTS student_subjects (
  id SERIAL PRIMARY KEY,
  student_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  UNIQUE (student_id, subject_id),
  CONSTRAINT fk_ss_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
  CONSTRAINT fk_ss_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- (Removed duplicate student_subjects block)

-- Map: instructor (user) <-> class
CREATE TABLE IF NOT EXISTS instructors_classes (
  id SERIAL PRIMARY KEY,
  class_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  UNIQUE (class_id, user_id),
  CONSTRAINT fk_ic_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  CONSTRAINT fk_ic_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Map: instructor (user) <-> class <-> subject (giảng viên dạy môn trong lớp)
CREATE TABLE IF NOT EXISTS instructors_class_subjects (
  id SERIAL PRIMARY KEY,
  class_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  UNIQUE (user_id, class_id, subject_id),
  CONSTRAINT fk_ics_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  CONSTRAINT fk_ics_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  CONSTRAINT fk_ics_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Faces (optional, store captured images or metadata)
CREATE TABLE IF NOT EXISTS faces (
  id SERIAL PRIMARY KEY,
  student_id INTEGER NOT NULL,
  image_path TEXT,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_faces_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Attendance Sessions
CREATE TABLE IF NOT EXISTS attendance_sessions (
  id SERIAL PRIMARY KEY,
  class_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  session_date DATE NOT NULL,
  time_slot VARCHAR(50),
  room VARCHAR(100),
  status VARCHAR(20) NOT NULL DEFAULT 'created', -- 'created' | 'started' | 'ended'
  session_code VARCHAR(12) UNIQUE, -- for QR / mobile join
  qr_code_path TEXT,
  created_by INTEGER,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_as_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
  CONSTRAINT fk_as_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  CONSTRAINT fk_as_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Attendance Records
CREATE TABLE IF NOT EXISTS attendance_records (
  id SERIAL PRIMARY KEY,
  session_id INTEGER NOT NULL,
  student_id INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL, -- 'present' | 'late' | 'absent'
  confidence DOUBLE PRECISION,
  device VARCHAR(20), -- 'laptop' | 'phone'
  image_path TEXT,
  captured_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, student_id),
  CONSTRAINT fk_ar_session FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
  CONSTRAINT fk_ar_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Settings
CREATE TABLE IF NOT EXISTS settings (
  name VARCHAR(50) PRIMARY KEY,
  value TEXT
);

-- Recognition history (used by existing features)
CREATE TABLE IF NOT EXISTS recognition_history (
  id SERIAL PRIMARY KEY,
  label TEXT,
  fullname TEXT,
  source TEXT,
  confidence DOUBLE PRECISION,
  captured_at TIMESTAMP NOT NULL DEFAULT NOW(),
  extra JSONB
);

-- Indexes to improve CRUD performance and FK lookups
CREATE INDEX IF NOT EXISTS idx_students_class_id ON students(class_id);
CREATE INDEX IF NOT EXISTS idx_students_face_label ON students(face_label);
CREATE INDEX IF NOT EXISTS idx_cs_class_id ON class_subjects(class_id);
CREATE INDEX IF NOT EXISTS idx_cs_subject_id ON class_subjects(subject_id);
CREATE INDEX IF NOT EXISTS idx_ss_student_id ON student_subjects(student_id);
CREATE INDEX IF NOT EXISTS idx_ss_subject_id ON student_subjects(subject_id);
CREATE INDEX IF NOT EXISTS idx_as_class_id ON attendance_sessions(class_id);
CREATE INDEX IF NOT EXISTS idx_as_subject_id ON attendance_sessions(subject_id);
CREATE INDEX IF NOT EXISTS idx_ar_session_id ON attendance_records(session_id);
CREATE INDEX IF NOT EXISTS idx_ar_student_id ON attendance_records(student_id);
CREATE INDEX IF NOT EXISTS idx_ics_user_id ON instructors_class_subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_ics_class_id ON instructors_class_subjects(class_id);
CREATE INDEX IF NOT EXISTS idx_ics_subject_id ON instructors_class_subjects(subject_id);

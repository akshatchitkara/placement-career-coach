-- Placement Career Coach -- learner state schema.
-- All tables: id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT (UTC ISO-8601).
-- Pragmas (set per connection, not here): journal_mode=WAL, foreign_keys=ON, busy_timeout=5000.

CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL UNIQUE,
    career_id TEXT,
    current_semester INTEGER CHECK (current_semester BETWEEN 3 AND 6),
    workflow_state TEXT NOT NULL DEFAULT 'PROFILE_READY',
    last_active_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE roadmaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    career_id TEXT NOT NULL,
    generation_source TEXT NOT NULL CHECK (generation_source IN ('template', 'ai_personalised', 'ai_drafted_unverified')),
    roadmap_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE assessment_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    attempt_type TEXT NOT NULL CHECK (attempt_type IN ('baseline', 'retest', 'full_path')),
    scope_description TEXT,
    shuffle_seed INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    overall_score REAL,
    level TEXT,
    level_notes_json TEXT,
    coverage_ratio REAL,
    config_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE assessment_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id),
    question_id TEXT NOT NULL,
    selected_option_id TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    displayed_order_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE skill_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id),
    skill_id TEXT NOT NULL,
    correct_count INTEGER NOT NULL,
    answered_count INTEGER NOT NULL,
    score REAL NOT NULL,
    has_sufficient_evidence INTEGER NOT NULL,
    is_weakest INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE coaching_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id),
    skill_id TEXT NOT NULL,
    generation_source TEXT NOT NULL CHECK (generation_source IN ('ai', 'template')),
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'superseded')),
    created_at TEXT NOT NULL
);

CREATE TABLE weekly_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id),
    week_start_date TEXT NOT NULL,
    retest_due_date TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    tasks_done_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

-- New in the AI-provider-configuration addendum (not in blueprint v3.0):
-- lets the student set provider/endpoint/key from the UI instead of .env.
-- Single-user local app -- see README for the "not multi-user-safe" caveat.
CREATE TABLE ai_provider_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_type TEXT NOT NULL CHECK (provider_type IN ('mock', 'anthropic', 'openai', 'nvidia', 'custom_openai_compatible')),
    base_url TEXT,
    api_key TEXT,
    model_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_attempts_profile_submitted ON assessment_attempts(profile_id, submitted_at);
CREATE INDEX idx_responses_attempt ON assessment_responses(attempt_id);
CREATE INDEX idx_skill_scores_attempt ON skill_scores(attempt_id);
CREATE INDEX idx_coaching_plans_profile_status ON coaching_plans(profile_id, status);

CREATE TABLE coaching_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    coaching_plan_id INTEGER NOT NULL REFERENCES coaching_plans(id),
    task_order INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'coach')),
    kind TEXT NOT NULL CHECK (kind IN ('explain_differently', 'example', 'question')),
    content TEXT NOT NULL,
    generation_source TEXT NOT NULL CHECK (generation_source IN ('ai', 'template', 'student')),
    created_at TEXT NOT NULL
);

CREATE INDEX idx_coaching_messages_task ON coaching_messages(coaching_plan_id, task_order);

-- Answers chosen so far in an open check, so a page reload does not lose them.
-- Deleted when the check is submitted. Never read by scoring.
CREATE TABLE assessment_drafts (
    attempt_id INTEGER PRIMARY KEY REFERENCES assessment_attempts(id),
    answers_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Careers students asked for that the catalog does not have yet (a wish list, never used by scoring).
CREATE TABLE career_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    requested_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- One row per roadmap module (skill) the student has taken the end-of-module quiz for.
-- passed_at is set the first time they get enough right. Never read by scoring.
CREATE TABLE module_progress (
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    skill_id TEXT NOT NULL,
    best_correct INTEGER NOT NULL,
    attempts INTEGER NOT NULL,
    passed_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (profile_id, skill_id)
);

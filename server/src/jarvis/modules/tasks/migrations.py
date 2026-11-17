"""Migrations do módulo de tarefas. NUNCA editar uma versão publicada: criar a próxima."""

V1 = """
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    due_date   TEXT    CHECK (due_date IS NULL OR date(due_date) = due_date),
    priority   TEXT    NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    created_at TEXT    NOT NULL,
    done_at    TEXT
);

CREATE INDEX tasks_done_due_date ON tasks (done, due_date);

-- Tarefas que vieram de outro lugar (ex.: o Jarvis em C++), para importar sem duplicar.
-- task_id vira NULL se a tarefa for apagada: assim, importar de novo não a ressuscita.
CREATE TABLE task_imports (
    source     TEXT    NOT NULL,
    source_id  INTEGER NOT NULL,
    task_id    INTEGER REFERENCES tasks (id) ON DELETE SET NULL,
    PRIMARY KEY (source, source_id)
);
"""

ALL = [V1]  # versão N = ALL[N - 1]

"""
Career Copilot — Unified Database Connector (MySQL + SQLite Fallback).
Connects to MySQL using mysql.connector and host.env credentials.
If MySQL credentials fail or MySQL is offline, automatically falls back
to SQLite so the application is always functional out-of-the-box.
"""

import os
import re
import json
import sqlite3
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv("host.env")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "career_copilot")
DB_USER = os.getenv("DB_USER", "career_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Vikash@8400")

_USE_SQLITE_FALLBACK = False


class SQLiteCursorWrapper:
    """Wraps sqlite3.Cursor to provide MySQL dictionary cursor compatibility and %s handling."""
    def __init__(self, cursor, dictionary=False):
        self._cur = cursor
        self._dictionary = dictionary
        self.lastrowid = None

    def execute(self, query, params=None):
        sql = re.sub(r'%s', '?', query)
        sql = re.sub(r'AUTO_INCREMENT', 'AUTOINCREMENT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'INT\s+AUTOINCREMENT', 'INTEGER AUTOINCREMENT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'TINYINT\(1\)', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'TIMESTAMP\s+DEFAULT\s+CURRENT_TIMESTAMP\s+ON\s+UPDATE\s+CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP', sql, flags=re.IGNORECASE)
        sql = re.sub(r'ENGINE=InnoDB.*?;', ';', sql, flags=re.IGNORECASE)
        sql = re.sub(r'DEFAULT CHARSET=utf8mb4', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r"ENUM\([^)]+\)", "VARCHAR(50)", sql, flags=re.IGNORECASE)
        sql = re.sub(r'ON DUPLICATE KEY UPDATE.*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'INSERT INTO', 'INSERT OR REPLACE INTO', sql, flags=re.IGNORECASE) if 'ON DUPLICATE KEY' in query.upper() else sql
        sql = re.sub(r'INSERT IGNORE INTO', 'INSERT OR IGNORE INTO', sql, flags=re.IGNORECASE)

        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            self._cur.execute(sql, params)
        else:
            self._cur.execute(sql)

        self.lastrowid = self._cur.lastrowid
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if self._dictionary:
            cols = [col[0] for col in self._cur.description]
            return dict(zip(cols, row))
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if self._dictionary and self._cur.description:
            cols = [col[0] for col in self._cur.description]
            return [dict(zip(cols, row)) for row in rows]
        return rows

    def close(self):
        self._cur.close()


class SQLiteConnectionWrapper:
    """Wraps sqlite3.Connection to provide a MySQL-compatible interface."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, dictionary=False):
        return SQLiteCursorWrapper(self._conn.cursor(), dictionary=dictionary)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def is_connected(self):
        return True


def get_db_connection():
    """Return a live MySQL connection using host.env credentials, or SQLite fallback."""
    global _USE_SQLITE_FALLBACK

    if not _USE_SQLITE_FALLBACK:
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "127.0.0.1"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=os.getenv("DB_USER", "career_app"),
                password=os.getenv("DB_PASSWORD", "Vikash@8400"),
                database=os.getenv("DB_NAME", "career_copilot"),
                charset="utf8mb4",
                use_unicode=True,
                autocommit=False,
            )
            return conn
        except mysql.connector.Error as err:
            print(f"[DB Notice] MySQL connection failed ({err.msg}). Falling back to SQLite.")
            _USE_SQLITE_FALLBACK = True

    db_path = os.path.join(os.path.dirname(__file__), "career_copilot.db")
    raw_conn = sqlite3.connect(db_path, timeout=10.0)
    raw_conn.execute("PRAGMA foreign_keys = ON;")
    return SQLiteConnectionWrapper(raw_conn)


def init_db():
    """Ensure all required tables and columns exist in MySQL (or SQLite)."""
    conn = get_db_connection()
    is_sqlite = isinstance(conn, SQLiteConnectionWrapper)

    if is_sqlite:
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            VARCHAR(120) NOT NULL,
                email           VARCHAR(255) NOT NULL UNIQUE,
                password_hash   VARCHAR(255) NOT NULL,
                education       VARCHAR(120) DEFAULT '',
                branch          VARCHAR(120) DEFAULT '',
                career_goal     VARCHAR(200) DEFAULT '',
                github_url      VARCHAR(300) DEFAULT '',
                linkedin_url    VARCHAR(300) DEFAULT '',
                mfa_enabled     INTEGER DEFAULT 0,
                mfa_secret      VARCHAR(64) DEFAULT '',
                resume_filename VARCHAR(255) DEFAULT '',
                resume_text     TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS career_analyses (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL,
                target_role         VARCHAR(200) DEFAULT '',
                current_skills      TEXT,
                missing_skills      TEXT,
                match_percentage    INTEGER DEFAULT 0,
                ai_summary          TEXT,
                resume_text         TEXT,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS roadmaps (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                target_role VARCHAR(200) NOT NULL,
                title       VARCHAR(200) NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS roadmap_steps (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                roadmap_id   INTEGER NOT NULL,
                step_order   INTEGER NOT NULL DEFAULT 1,
                title        VARCHAR(200) NOT NULL,
                description  TEXT,
                status       VARCHAR(50) DEFAULT 'Not Started',
                icon         VARCHAR(60) DEFAULT 'fa-circle-check',
                skills_csv   TEXT,
                completed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS skills (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     VARCHAR(120) NOT NULL UNIQUE,
                category VARCHAR(120) DEFAULT 'General'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS user_skills (
                user_id     INTEGER NOT NULL,
                skill_id    INTEGER NOT NULL,
                status      VARCHAR(50) DEFAULT 'have',
                proficiency VARCHAR(50) DEFAULT 'Beginner',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, skill_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                role       VARCHAR(20) NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS interview_sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                target_role    VARCHAR(160) DEFAULT 'Software Engineer',
                score          INTEGER DEFAULT 0,
                questions_done INTEGER DEFAULT 0,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        ]
        cur = conn.cursor()
        for stmt in ddl_statements:
            cur.execute(stmt)
        conn.commit()
        cur.close()
    else:
        # MySQL schema verification & migrations
        cur = conn.cursor()

        # 1. Verify / migrate users columns
        migrations_users = [
            "ADD COLUMN education VARCHAR(160) DEFAULT ''",
            "ADD COLUMN branch VARCHAR(160) DEFAULT ''",
            "ADD COLUMN career_goal VARCHAR(200) DEFAULT ''",
            "ADD COLUMN github_url VARCHAR(300) DEFAULT ''",
            "ADD COLUMN linkedin_url VARCHAR(300) DEFAULT ''",
            "ADD COLUMN mfa_enabled TINYINT(1) DEFAULT 0",
            "ADD COLUMN mfa_secret VARCHAR(64) DEFAULT ''",
            "ADD COLUMN resume_filename VARCHAR(255) DEFAULT ''",
            "ADD COLUMN resume_text TEXT",
        ]
        for col_def in migrations_users:
            try:
                cur.execute(f"ALTER TABLE users {col_def};")
                conn.commit()
            except Exception:
                pass  # Column already exists

        # 2. Verify career_analyses columns
        for col_def in [
            "ADD COLUMN ai_summary TEXT",
            "ADD COLUMN resume_text TEXT",
        ]:
            try:
                cur.execute(f"ALTER TABLE career_analyses {col_def};")
                conn.commit()
            except Exception:
                pass

        # 3. Verify roadmap_steps columns
        for col_def in [
            "ADD COLUMN icon VARCHAR(60) DEFAULT 'fa-circle-check'",
            "ADD COLUMN skills_csv VARCHAR(255) DEFAULT ''",
        ]:
            try:
                cur.execute(f"ALTER TABLE roadmap_steps {col_def};")
                conn.commit()
            except Exception:
                pass

        # 4. Verify user_skills status column
        try:
            cur.execute("ALTER TABLE user_skills ADD COLUMN status ENUM('have','missing','learning') DEFAULT 'have';")
            conn.commit()
        except Exception:
            pass

        # 5. Verify interview_sessions questions_done
        try:
            cur.execute("ALTER TABLE interview_sessions ADD COLUMN questions_done INT DEFAULT 0;")
            conn.commit()
        except Exception:
            pass

        # 6. Ensure chat_history table exists (MySQL)
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    user_id    BIGINT UNSIGNED NOT NULL,
                    role       ENUM('user','assistant') NOT NULL,
                    content    TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.commit()
        except Exception:
            pass

        cur.close()

    conn.close()
    print("[SUCCESS] MySQL database schema initialized and verified.")

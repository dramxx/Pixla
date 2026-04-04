import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from app.models import Generation, Palette, GenerationStatus


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS palettes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    colors TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    system_prompt TEXT,
                    colors TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    model TEXT,
                    sprite_type TEXT NOT NULL,
                    pixel_data TEXT,
                    iterations INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    image_path TEXT,
                    reference_path TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generations_status 
                ON generations(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generations_created_at 
                ON generations(created_at DESC)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation_id INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (generation_id) REFERENCES generations(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_generation_logs_gen_id 
                ON generation_logs(generation_id)
            """)
            conn.commit()

            row = conn.execute("SELECT COUNT(*) as cnt FROM palettes").fetchone()
            if row["cnt"] == 0:
                self._create_default_palette(conn)

    def _create_default_palette(self, conn):
        default_colors = [
            "#000000",
            "#FFFFFF",
            "#8B4513",
            "#C0C0C0",
            "#FF0000",
            "#00FF00",
            "#0000FF",
            "#FFFF00",
        ]
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO palettes (name, colors, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("Default", json.dumps(default_colors), now, now),
        )
        conn.commit()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_palette(self, name: str, colors: List[str]) -> Palette:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO palettes (name, colors, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (name, json.dumps(colors), now, now),
            )
            conn.commit()
            return Palette(
                id=cursor.lastrowid,
                name=name,
                colors=colors,
                created_at=now,
                updated_at=now,
            )

    def list_palettes(self) -> List[Palette]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM palettes ORDER BY created_at DESC").fetchall()
            return [self._row_to_palette(r) for r in rows]

    def get_palette(self, palette_id: int) -> Optional[Palette]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM palettes WHERE id = ?", (palette_id,)).fetchone()
            if not row:
                return None
            return self._row_to_palette(row)

    def update_palette(self, palette_id: int, name: str, colors: List[str]) -> Optional[Palette]:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE palettes SET name = ?, colors = ?, updated_at = ? WHERE id = ?",
                (name, json.dumps(colors), now, palette_id),
            )
            conn.commit()
        return self.get_palette(palette_id)

    def delete_palette(self, palette_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM palettes WHERE id = ?", (palette_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_palette(self, row) -> Palette:
        return Palette(
            id=row["id"],
            name=row["name"],
            colors=json.loads(row["colors"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_generation(
        self,
        prompt: str,
        colors: List[str],
        size: int,
        sprite_type: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Generation:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO generations 
                   (prompt, colors, size, sprite_type, system_prompt, model, status, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    prompt,
                    json.dumps(colors),
                    size,
                    sprite_type,
                    system_prompt,
                    model,
                    GenerationStatus.PENDING.value,
                    now,
                    now,
                ),
            )
            conn.commit()
            return Generation(
                id=cursor.lastrowid,
                prompt=prompt,
                colors=colors,
                size=size,
                sprite_type=sprite_type,
                system_prompt=system_prompt,
                model=model,
                status=GenerationStatus.PENDING,
                created_at=now,
                updated_at=now,
            )

    def get_generation(self, gen_id: int) -> Optional[Generation]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM generations WHERE id = ?", (gen_id,)).fetchone()
            if not row:
                return None
            return self._row_to_generation(row)

    def list_generations(self, limit: int = 50, offset: int = 0) -> List[Generation]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM generations ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._row_to_generation(r) for r in rows]

    def update_generation_status(
        self, gen_id: int, status: GenerationStatus, error_message: Optional[str] = None
    ):
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE generations SET status = ?, updated_at = ?, error_message = ? WHERE id = ?",
                (status.value, now, error_message, gen_id),
            )
            conn.commit()

    def update_generation_pixels(self, gen_id: int, pixel_data: List[List[int]], iterations: int):
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE generations SET pixel_data = ?, iterations = ?, status = ?, updated_at = ? WHERE id = ?",
                (
                    json.dumps(pixel_data),
                    iterations,
                    GenerationStatus.COMPLETE.value,
                    now,
                    gen_id,
                ),
            )
            conn.commit()

    def update_generation_image(self, gen_id: int, image_path: str):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE generations SET image_path = ? WHERE id = ?",
                (image_path, gen_id),
            )
            conn.commit()

    def update_generation_reference(self, gen_id: int, reference_path: str):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE generations SET reference_path = ? WHERE id = ?",
                (reference_path, gen_id),
            )
            conn.commit()

    def _row_to_generation(self, row) -> Generation:
        return Generation(
            id=row["id"],
            prompt=row["prompt"],
            system_prompt=row["system_prompt"],
            colors=json.loads(row["colors"]),
            size=row["size"],
            model=row["model"],
            sprite_type=row["sprite_type"],
            pixel_data=json.loads(row["pixel_data"]) if row["pixel_data"] else None,
            iterations=row["iterations"],
            status=GenerationStatus(row["status"]),
            image_path=row["image_path"],
            reference_path=row["reference_path"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_log(self, gen_id: int, step: str, message: str):
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO generation_logs (generation_id, step, message, created_at) VALUES (?, ?, ?, ?)",
                (gen_id, step, message, now),
            )
            conn.commit()

    def get_logs(self, gen_id: int) -> List[dict]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM generation_logs WHERE generation_id = ? ORDER BY created_at ASC",
                (gen_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "step": r["step"],
                    "message": r["message"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

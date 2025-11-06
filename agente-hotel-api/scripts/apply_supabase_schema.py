#!/usr/bin/env python3
"""
Aplica el archivo SQL de esquema a una base de datos Postgres (Supabase) de forma segura.

Características:
- Carga DATABASE_URL desde el entorno o desde .env (si existe) sin dependencias externas.
- Parser de SQL que respeta strings, comentarios y bloques dollar-quoted ($$...$$),
  para dividir statements por ';' correctamente.
- Ejecuta todas las sentencias en una transacción; si algo falla, se hace rollback.
- Guarda un log resumido de la ejecución en logs/supabase_schema_apply_<timestamp>.log

Uso:
  python scripts/apply_supabase_schema.py \
    --schema-file docs/supabase/schema.sql [--dry-run]

Requisitos:
- asyncpg ya está en las dependencias del proyecto.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

import asyncpg


def load_env_file_if_present(dotenv_path: Path) -> None:
    """Carga variables de un .env de forma sencilla (solo líneas KEY=VALUE)."""
    if not dotenv_path.exists():
        return
    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            # Elimina comillas de envoltura si existen
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception as e:
        print(f"⚠️  No se pudo cargar {dotenv_path}: {e}")


def parse_sql_statements(sql_text: str) -> List[str]:
    """Divide un script SQL en sentencias individuales respetando contextos.

    Maneja:
    - Strings con ' y "
    - Comentarios de línea -- y de bloque /* */
    - Dollar-quoted bodies $$...$$ y $tag$...$tag$
    """
    statements: List[str] = []
    buf: List[str] = []
    i = 0
    n = len(sql_text)
    in_squote = False
    in_dquote = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: str | None = None

    def peek(k: int = 1) -> str:
        return sql_text[i + k] if i + k < n else ""

    while i < n:
        ch = sql_text[i]
        nxt = peek(1)

        # Comentario de línea
        if not in_squote and not in_dquote and not in_block_comment and dollar_tag is None:
            if ch == '-' and nxt == '-':
                in_line_comment = True
        if in_line_comment:
            buf.append(ch)
            if ch == '\n':
                in_line_comment = False
            i += 1
            continue

        # Comentario de bloque
        if not in_squote and not in_dquote and dollar_tag is None:
            if not in_block_comment and ch == '/' and nxt == '*':
                in_block_comment = True
            elif in_block_comment and ch == '*' and nxt == '/':
                buf.append(ch)
                buf.append(nxt)
                i += 2
                in_block_comment = False
                continue
        if in_block_comment:
            buf.append(ch)
            i += 1
            continue

        # Dollar-quoted
        if not in_squote and not in_dquote:
            if dollar_tag is None and ch == '$':
                # Detecta $tag$ o $$
                j = i + 1
                while j < n and sql_text[j].isalnum() or (j < n and sql_text[j] == '_'):
                    j += 1
                if j < n and sql_text[j] == '$':
                    tag = sql_text[i : j + 1]
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
            elif dollar_tag is not None and ch == '$':
                # ¿Cierre del mismo tag?
                tag = dollar_tag
                if sql_text.startswith(tag, i):
                    buf.append(tag)
                    i += len(tag)
                    dollar_tag = None
                    continue

        # Strings
        if dollar_tag is None and not in_dquote and ch == "'":
            in_squote = not in_squote
        elif dollar_tag is None and not in_squote and ch == '"':
            in_dquote = not in_dquote

        # Separación por ';' solo si estamos fuera de strings, comentarios y dollar-quoted
        if ch == ';' and not in_squote and not in_dquote and not in_block_comment and not in_line_comment and dollar_tag is None:
            stmt = ''.join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    # Último buffer
    tail = ''.join(buf).strip()
    if tail:
        statements.append(tail)

    return statements


async def apply_schema(database_url: str, schema_file: Path, dry_run: bool = False) -> None:
    if not schema_file.exists():
        print(f"❌ No se encontró el archivo de esquema: {schema_file}")
        sys.exit(1)

    sql_text = schema_file.read_text(encoding="utf-8")
    statements = parse_sql_statements(sql_text)
    print(f"🗃️  Archivo: {schema_file} | Sentencias detectadas: {len(statements)}")

    if dry_run:
        for idx, st in enumerate(statements, 1):
            print(f"--- Statement {idx} ---\n{st}\n----------------------")
        print("(dry-run) ✔️  Fin del volcado de statements")
        return

    # Conexión y transacción
    start = time.time()
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            for idx, st in enumerate(statements, 1):
                try:
                    await conn.execute(st)
                    print(f"✅ [{idx}/{len(statements)}] OK")
                except Exception as stmt_err:
                    print(f"❌ Error en statement {idx}: {stmt_err}\n--- SQL ---\n{st}\n-----------")
                    raise
    finally:
        await conn.close()

    elapsed = time.time() - start
    print(f"🎉 Esquema aplicado en {elapsed:.2f}s")

    # Guardar log mínimo
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"supabase_schema_apply_{ts}.log"
    log_path.write_text(
        f"schema_file={schema_file}\nstatements={len(statements)}\nelapsed_seconds={elapsed:.2f}\n", encoding="utf-8"
    )
    print(f"📝 Log: {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica schema.sql a Supabase/Postgres")
    parser.add_argument("--schema-file", default="docs/supabase/schema.sql", help="Ruta al archivo schema.sql")
    parser.add_argument("--dry-run", action="store_true", help="No ejecuta; imprime statements parseados")
    args = parser.parse_args()

    # Cargar .env si existe (sin dependencia extra)
    load_env_file_if_present(Path(".env"))
    load_env_file_if_present(Path(".env.supabase"))

    database_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        print("❌ Falta DATABASE_URL (o SUPABASE_DATABASE_URL) en el entorno/.env")
        sys.exit(1)

    # Recomendación SSL
    if "sslmode=require" not in database_url:
        print("⚠️  Recomendado incluir sslmode=require en DATABASE_URL para Supabase")

    schema_path = Path(args.schema_file)
    try:
        asyncio.run(apply_schema(database_url, schema_path, dry_run=args.dry_run))
    except KeyboardInterrupt:
        print("Interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Falló la aplicación del esquema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

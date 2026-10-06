#!/bin/bash
set -euo pipefail

DEFAULT_MYSQL_HOST="localhost"
DEFAULT_MYSQL_PORT="3306"
DEFAULT_MYSQL_USER="root"
DEFAULT_MYSQL_PASSWORD="Zhao1029*"
DEFAULT_MYSQL_BIN="/usr/local/mysql/bin/mysql"

HOST="${MYSQL_HOST:-$DEFAULT_MYSQL_HOST}"
PORT="${MYSQL_PORT:-$DEFAULT_MYSQL_PORT}"
USER="${MYSQL_USER:-$DEFAULT_MYSQL_USER}"
PASSWORD="${MYSQL_PWD:-$DEFAULT_MYSQL_PASSWORD}"
DATABASE="${MYSQL_DATABASE:-auto}"
AUTHOR_USER_ID=""
MYSQL_BIN="${MYSQL_BIN:-$DEFAULT_MYSQL_BIN}"
SQL_FILES=()

usage() {
  cat >&2 <<'EOF'
Usage:
  execute_content_article_sql.sh [options] /path/to/import_content_article.sql [...]

Options:
  --host HOST                 MySQL host. Default: MYSQL_HOST or built-in localhost.
  --port PORT                 MySQL port. Default: MYSQL_PORT or built-in 3306.
  --user USER                 MySQL user. Default: MYSQL_USER or built-in root.
  --password PASSWORD         MySQL password. Default: MYSQL_PWD or built-in local password.
  --database DATABASE         Target database. Default: MYSQL_DATABASE or auto-detect.
  --author-user-id USER_ID    Override SET @AUTHOR_USER_ID in a temporary SQL copy.
  --mysql-bin PATH            mysql client path. Default: MYSQL_BIN or built-in /usr/local/mysql/bin/mysql.

Environment defaults:
  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PWD, MYSQL_DATABASE, MYSQL_BIN

Built-in local defaults:
  localhost:3306, user root, auto-detected SparkService database.

Auto-detection:
  When --database/MYSQL_DATABASE is omitted or set to "auto", the script selects
  the only schema containing the required SparkService tables. If none or
  multiple schemas match, pass --database explicitly.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      HOST="$2"; shift 2 ;;
    --port)
      PORT="$2"; shift 2 ;;
    --user)
      USER="$2"; shift 2 ;;
    --password)
      PASSWORD="$2"; shift 2 ;;
    --database)
      DATABASE="$2"; shift 2 ;;
    --author-user-id)
      AUTHOR_USER_ID="$2"; shift 2 ;;
    --mysql-bin)
      MYSQL_BIN="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do SQL_FILES+=("$1"); shift; done ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2 ;;
    *)
      SQL_FILES+=("$1"); shift ;;
  esac
done

if [ "${#SQL_FILES[@]}" -eq 0 ]; then
  echo "No SQL files provided." >&2
  usage
  exit 2
fi

if ! command -v "$MYSQL_BIN" >/dev/null 2>&1; then
  echo "mysql client not found: $MYSQL_BIN" >&2
  exit 127
fi

mysql_exec() {
  MYSQL_PWD="$PASSWORD" "$MYSQL_BIN" \
    -h "$HOST" \
    -P "$PORT" \
    -u "$USER" \
    --default-character-set=utf8mb4 \
    "$@"
}

echo "Checking MySQL connection and target database..." >&2
if [ "$DATABASE" = "auto" ]; then
  candidate_databases=()
  while IFS= read -r candidate_database; do
    [ -z "$candidate_database" ] || candidate_databases+=("$candidate_database")
  done < <(mysql_exec -N -e "
    SELECT TABLE_SCHEMA
    FROM information_schema.TABLES
    WHERE TABLE_NAME IN (
      'auth_user',
      'content_articles',
      'content_categories',
      'content_tags',
      'content_article_tags',
      'file_manager_managedfile',
      'file_manager_managedfilebusinessrelation'
    )
    GROUP BY TABLE_SCHEMA
    HAVING COUNT(DISTINCT TABLE_NAME) = 7
    ORDER BY TABLE_SCHEMA;
  ")
  if [ "${#candidate_databases[@]}" -eq 1 ]; then
    DATABASE="${candidate_databases[0]}"
    echo "Auto-detected SparkService database: $DATABASE" >&2
  elif [ "${#candidate_databases[@]}" -eq 0 ]; then
    echo "Could not auto-detect a SparkService database with all required tables." >&2
    exit 1
  else
    echo "Multiple SparkService-like databases found: ${candidate_databases[*]}" >&2
    echo "Pass --database explicitly." >&2
    exit 1
  fi
else
  mysql_exec -N -e "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '${DATABASE//\'/\'\'}';" | grep -qx "$DATABASE" || {
    echo "Database not found: $DATABASE" >&2
    exit 1
  }
fi

if [ -n "$AUTHOR_USER_ID" ]; then
  mysql_exec "$DATABASE" -N -e "SELECT id FROM auth_user WHERE id = ${AUTHOR_USER_ID} LIMIT 1;" | grep -qx "$AUTHOR_USER_ID" || {
    echo "auth_user.id not found: $AUTHOR_USER_ID" >&2
    exit 1
  }
fi

for sql_file in "${SQL_FILES[@]}"; do
  if [ ! -f "$sql_file" ]; then
    echo "SQL file not found: $sql_file" >&2
    exit 1
  fi

  tmp_file=""
  input_file="$sql_file"
  if [ -n "$AUTHOR_USER_ID" ]; then
    tmp_file="$(mktemp "${TMPDIR:-/tmp}/content-import.XXXXXX.sql")"
    sed -E "s/^SET @AUTHOR_USER_ID := [0-9]+;/SET @AUTHOR_USER_ID := ${AUTHOR_USER_ID};/" "$sql_file" > "$tmp_file"
    input_file="$tmp_file"
  fi

  echo "Executing: $sql_file" >&2
  mysql_exec "$DATABASE" < "$input_file"
  [ -z "$tmp_file" ] || rm -f "$tmp_file"
done

echo "Content article SQL execution completed." >&2

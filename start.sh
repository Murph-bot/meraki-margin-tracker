#!/bin/sh
# Container entrypoint. Runs uvicorn directly, or under Litestream when replication to
# R2 is fully configured (docs/litestream.md). Never prints secret values.
set -eu

# Overridable so tests can substitute fakes; defaults are the production values.
APP_DIR="${APP_DIR:-/app/backend}"
LITESTREAM_BIN="${LITESTREAM_BIN:-litestream}"
LITESTREAM_CONFIG="${LITESTREAM_CONFIG:-/app/litestream.yml}"
PORT="${PORT:-8000}"

# Resolve the DB path exactly like backend/app/config.py: the Railway volume wins,
# then DATABASE_PATH, then data/meraki.db relative to the app dir.
if [ -n "${RAILWAY_VOLUME_MOUNT_PATH:-}" ]; then
    db_path="${RAILWAY_VOLUME_MOUNT_PATH}/meraki.db"
elif [ -n "${DATABASE_PATH:-}" ]; then
    db_path="${DATABASE_PATH}"
else
    db_path="data/meraki.db"
fi
case "$db_path" in
    /*) ;;
    *) db_path="${APP_DIR}/${db_path}" ;;
esac
export LITESTREAM_DB_PATH="$db_path"
mkdir -p "$(dirname "$db_path")"

run_plain() {
    cd "$APP_DIR"
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
}

if [ "${LITESTREAM_DISABLE:-}" = "1" ]; then
    echo "start.sh: LITESTREAM_DISABLE=1, starting without replication" >&2
    run_plain
fi

set_count=0
missing=""
for name in LITESTREAM_REPLICA_URL LITESTREAM_ACCESS_KEY_ID LITESTREAM_SECRET_ACCESS_KEY LITESTREAM_ENDPOINT; do
    eval "value=\${$name:-}"
    if [ -n "$value" ]; then
        set_count=$((set_count + 1))
    else
        missing="${missing:+$missing, }$name"
    fi
done

if [ "$set_count" -eq 0 ]; then
    run_plain
elif [ "$set_count" -lt 4 ]; then
    echo "start.sh: WARNING: Litestream replication disabled, missing variables: ${missing}" >&2
    run_plain
fi

if [ ! -f "$db_path" ]; then
    echo "start.sh: no database at ${db_path}, restoring from replica if one exists" >&2
    # A failure here must stop the boot: starting would create an empty DB, which
    # Litestream would then replicate over the real backup.
    "$LITESTREAM_BIN" restore -config "$LITESTREAM_CONFIG" \
        -if-db-not-exists -if-replica-exists "$db_path" || {
        echo "start.sh: ERROR: litestream restore failed, refusing to start with an empty database" >&2
        exit 1
    }
fi

cd "$APP_DIR"
exec "$LITESTREAM_BIN" replicate -config "$LITESTREAM_CONFIG" \
    -exec "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"

#!/bin/sh
set -e
cd /app/backend
python -c "import os, sqlite3; p = os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', 'data'), 'meraki.db'); c = sqlite3.connect('file:' + p + '?mode=ro', uri=True); r = c.execute('SELECT id, email, created_at FROM users ORDER BY id').fetchall(); print('MERAKI_USERS: count=%d %s' % (len(r), r))" || echo "MERAKI_USERS: query failed"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

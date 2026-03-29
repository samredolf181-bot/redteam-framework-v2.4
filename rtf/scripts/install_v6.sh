#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install -r requirements.txt
mkdir -p data/evidence data/dossiers plugins templates/dossiers
python3 - <<'PY'
from framework.db.database import db
from framework.core.config import config
db.init(config.get('db_path','data/framework.db'))
print('DB initialized')
PY

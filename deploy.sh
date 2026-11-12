#!/bin/sh
# Deploy Zócalo with Docker. Run it from anywhere; it works in the folder it lives in.
#
#   ./deploy.sh                          # defaults: port 8730, ./data, ./datasets, sign-in on
#   ./deploy.sh --personal-no-pass       # no sign-in: for one person on their own machine
#   ./deploy.sh --port 9000 --data-dir /srv/zocalo/data --datasets-dir /mnt/big/zocalo
#   ./deploy.sh --down                   # stop it
set -eu
cd "$(dirname "$0")"

PORT=8730
DATA_DIR=./data
DATASETS_DIR=./datasets
AUTH=accounts
DOWN=0
[ -f .env ] && . ./.env 2>/dev/null || true
PORT=${ZOCALO_PORT:-$PORT}; DATA_DIR=${ZOCALO_DATA_DIR:-$DATA_DIR}
DATASETS_DIR=${ZOCALO_DATASETS_DIR:-$DATASETS_DIR}; AUTH=${ZOCALO_AUTH:-$AUTH}

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --datasets-dir) DATASETS_DIR="$2"; shift 2 ;;
    --personal-no-pass) AUTH=none; shift ;;
    --with-auth) AUTH=accounts; shift ;;
    --down) DOWN=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1"; usage 1 ;;
  esac
done

command -v docker >/dev/null 2>&1 || { echo "Docker is needed: https://docs.docker.com/get-docker/"; exit 1; }
if [ "$DOWN" = 1 ]; then docker compose down; exit 0; fi
case "$PORT" in ''|*[!0-9]*) echo "--port must be a number"; exit 1 ;; esac

mkdir -p "$DATA_DIR"
if [ ! -d "$DATASETS_DIR" ]; then
  echo "Dataset folder $DATASETS_DIR doesn't exist; creating it."
  mkdir -p "$DATASETS_DIR"
fi
cat > .env <<ENV
ZOCALO_PORT=$PORT
ZOCALO_DATA_DIR=$DATA_DIR
ZOCALO_DATASETS_DIR=$DATASETS_DIR
ZOCALO_AUTH=$AUTH
ENV
# The sign-in choice is applied on first start. Switching an existing install to no sign-in is deliberate:
if [ "$AUTH" = none ] && [ -f "$DATA_DIR/zocalo.db" ]; then
  echo "Note: an existing install keeps its sign-in setting. Sign-in can be turned on in Settings; it is never turned off silently."
fi
docker compose up -d --build
echo
echo "Zócalo is starting on port $PORT:  http://localhost:$PORT"
[ "$AUTH" = none ] && echo "Running WITHOUT sign-in. Anyone who can reach this port can use it."
echo "Back up $DATA_DIR (database, encrypted keys). $DATASETS_DIR holds downloads you can fetch again."

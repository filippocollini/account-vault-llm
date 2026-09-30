#!/bin/sh
# Wrapper unico per il lint del vault. Lo usano il git hook, lo slash command di
# Claude Code, e qualunque scheduler: così esiste una sola invocazione da mantenere.
#
#   tools/lint/run.sh            report completo + exit 1 sugli ERROR oltre soglia
#   tools/lint/run.sh --quiet    solo il conteggio, nessun report scritto (per gli hook)

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Il vault demo fissa la propria data in .vault-today: senza, le deal "scadono" col calendario.
if [ -z "$VAULT_TODAY" ] && [ -f "$ROOT/.vault-today" ]; then
    VAULT_TODAY="$(head -1 "$ROOT/.vault-today")"; export VAULT_TODAY
fi
BASELINE="$(sed -n 's/^[^0-9]*\([0-9][0-9]*\).*/\1/p' "$ROOT/tools/lint/error-baseline.txt" 2>/dev/null | head -1)"
[ -n "$BASELINE" ] || BASELINE=0

if [ "$1" = "--quiet" ]; then
    exec python3 "$ROOT/tools/lint/vault.py" --root "$ROOT" --no-report --max-errors "$BASELINE"
fi

python3 "$ROOT/tools/lint/vault.py" --root "$ROOT" --max-errors "$BASELINE"
STATUS=$?
echo
echo "Report completo: wiki/meta/lint-report.md"
echo "Soglia attuale: $BASELINE ERROR (tools/lint/error-baseline.txt) — abbassala quando ne chiudi"
exit $STATUS

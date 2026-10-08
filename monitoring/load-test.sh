#!/usr/bin/env bash
# Opens, works and resolves incidents in a loop so every dashboard panel has data.
# No -e: one refused request during a scale out should not end the run.
set -uo pipefail

BASE_URL="${BASE_URL:-http://incidents.localhost:18220}"
DURATION="${DURATION:-120}"
json='Content-Type: application/json'
severities=(SEV1 SEV2 SEV3 SEV4)
services=(checkout payments search auth)

end=$((SECONDS + DURATION))
requests=0
while [ "$SECONDS" -lt "$end" ]; do
  sev=${severities[RANDOM % 4]}
  svc=${services[RANDOM % 4]}
  id=$(curl -s -X POST "$BASE_URL/api/incidents" -H "$json" \
    -d "{\"title\":\"load test on $svc\",\"service\":\"$svc\",\"severity\":\"$sev\"}" | sed -E 's/^\{"id":([0-9]+).*/\1/')
  [[ "$id" =~ ^[0-9]+$ ]] || continue
  curl -s -o /dev/null -X POST "$BASE_URL/api/incidents/$id/notes" -H "$json" -d '{"body":"looking"}'
  curl -s -o /dev/null "$BASE_URL/api/incidents?status=open"
  curl -s -o /dev/null "$BASE_URL/api/incidents?severity=$sev"
  curl -s -o /dev/null "$BASE_URL/api/stats"
  if [ $((RANDOM % 3)) -ne 0 ]; then
    curl -s -o /dev/null -X POST "$BASE_URL/api/incidents/$id/status" -H "$json" -d '{"status":"resolved"}'
  fi
  requests=$((requests + 6))
done
echo "sent $requests requests to $BASE_URL in ${DURATION}s"

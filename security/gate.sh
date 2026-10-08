#!/usr/bin/env bash
# Usage: gate.sh "Check name=result count" ...
# result is the scanner job result (success, failure, skipped). A check passes only
# when its job succeeded and reported a count of zero, so a crashed scanner blocks.
set -uo pipefail

summary="${GITHUB_STEP_SUMMARY:-/dev/null}"
failed=0
printf '| Check | Findings | Verdict |\n|---|---|---|\n' | tee -a "$summary"
for arg in "$@"; do
  name="${arg%%=*}"
  read -r result count <<< "${arg#*=}"
  if [ "$result" != "success" ] || ! [[ "${count:-}" =~ ^[0-9]+$ ]]; then
    verdict="BLOCK (job $result)"; failed=1
  elif [ "$count" -gt 0 ]; then
    verdict="BLOCK"; failed=1
  else
    verdict="pass"
  fi
  printf '| %s | %s | %s |\n' "$name" "${count:-none}" "$verdict" | tee -a "$summary"
done

if [ "$failed" -ne 0 ]; then
  echo "::error::Security gate failed. Images will not be pushed or deployed."
  exit 1
fi
echo "Security gate passed."

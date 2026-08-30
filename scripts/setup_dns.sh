#!/usr/bin/env bash
# Grey-cloud A + www CNAME for reasonreader.com.
# Reads CLOUDFLARE_API_TOKEN or CF_API_TOKEN from the environment or CF_ENV file.
set -euo pipefail

ZONE_NAME="${ZONE_NAME:-reasonreader.com}"
TARGET_IP="${TARGET_IP:-144.126.135.134}"
CF_ENV="${CF_ENV:-}"

if [[ -n "$CF_ENV" && -r "$CF_ENV" ]]; then
  # shellcheck disable=SC1090
  set -a && . "$CF_ENV" && set +a
fi

TOKEN="${CLOUDFLARE_API_TOKEN:-${CF_API_TOKEN:-}}"
[[ -n "$TOKEN" ]] || {
  echo "set CLOUDFLARE_API_TOKEN or CF_ENV" >&2
  exit 1
}

cf() {
  local method="$1" path="$2" body="${3:-}"
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "https://api.cloudflare.com/client/v4${path}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$body"
  else
    curl -sS -X "$method" "https://api.cloudflare.com/client/v4${path}" \
      -H "Authorization: Bearer ${TOKEN}"
  fi
}

ZONE_ID="$(cf GET "/zones?name=${ZONE_NAME}" | jq -r '.result[0].id // empty')"
[[ -n "$ZONE_ID" ]] || {
  echo "zone ${ZONE_NAME} not visible to this token" >&2
  exit 1
}

upsert() {
  local type="$1" name="$2" content="$3"
  local existing record_id payload result
  existing="$(cf GET "/zones/${ZONE_ID}/dns_records?type=${type}&name=${name}")"
  record_id="$(jq -r '.result[0].id // empty' <<<"$existing")"
  payload="$(jq -nc --arg type "$type" --arg name "$name" --arg content "$content" \
    '{type:$type, name:$name, content:$content, ttl:120, proxied:false}')"
  if [[ -z "$record_id" ]]; then
    result="$(cf POST "/zones/${ZONE_ID}/dns_records" "$payload")"
  else
    result="$(cf PUT "/zones/${ZONE_ID}/dns_records/${record_id}" "$payload")"
  fi
  jq -e '.success' >/dev/null <<<"$result" || {
    echo "failed ${type} ${name}: $(jq -c '.errors' <<<"$result")" >&2
    exit 1
  }
  echo "ok ${type} ${name} -> ${content} (proxied=false)"
}

upsert A "$ZONE_NAME" "$TARGET_IP"
upsert CNAME "www.${ZONE_NAME}" "$ZONE_NAME"

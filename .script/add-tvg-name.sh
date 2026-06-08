#!/bin/bash
# Fügt tvg-id + tvg-name Attribute in M3U-Dateien hinzu, basierend auf iptv-epg.org EPG.
# Aufruf: ./add-tvg-name.sh [m3u-datei ...]
# Ohne Argument: verarbeitet alle .m3u Dateien im m3u/ Ordner

set -euo pipefail

EPG_URL="https://iptv-epg.org/files/epg-de.xml"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
M3U_DIR="$(cd "$SCRIPT_DIR/../m3u" && pwd)"
TMP_EPG="/tmp/epg_tv_$$.xml"
TMP_MAP="/tmp/epg_map_$$.txt"
TMP_ALIAS="/tmp/epg_alias_$$.txt"

cleanup() { rm -f "$TMP_EPG" "$TMP_MAP" "$TMP_ALIAS"; }
trap cleanup EXIT

echo "=== EPG von iptv-epg.org laden ..."
curl -sL "$EPG_URL" -o "$TMP_EPG" || { echo "FEHLER: EPG nicht ladbar"; exit 1; }

# Manuelle Aliase für nicht-triviale M3U↔EPG Namensunterschiede
cat > "$TMP_ALIAS" << 'EOF'
aljazeeraint|Al Jazeera English
bbcnews|BBC World
dmf|Deutsches Musik Fernsehen
swrfernsehenrp|SWR RP
swrrp|SWR RP
cnbceurope|CNBC International
cnn|CNN International
nhkworldjapan|NHK WORLD-JAPAN
EOF

# Baue Mapping-Datei aus EPG: normalisierter_Key|tvg-id|tvg-name(voll)
# tvg-id = channel id, tvg-name = display-name (mit "DE - " Prefix)
sed -n '
/channel id="/{
  h
  n
  /display-name/{
    H
    x
    s/.*channel id="\([^"]*\)".*\n.*<display-name[^>]*>\([^<]*\)<.*/\1|\2/
    s/|DE - /|/
    p
  }
}' "$TMP_EPG" | while IFS='|' read -r tvg_id display_name; do
  clean_name="$display_name"
  normalized=$(echo "$clean_name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
  echo "${normalized}|${tvg_id}|${display_name}"
done > "$TMP_MAP"

total_epg=$(wc -l < "$TMP_MAP")
echo "   $total_epg EPG-Kanäle geladen"

map_channel() {
  local m3u_name="$1"
  # Normiere: HD-Suffix entfernen, Klammern, führende Doppelpunkte
  local clean=$(echo "$m3u_name" | sed 's/ *[Hh][Dd]$//; s/ *(eng)$//; s/ *(fre)$//; s/^://' | sed 's/[[:space:]]*$//')
  local normalized=$(echo "$clean" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')

  # 0. Manuelle Aliase prüfen
  while IFS='|' read -r alias_key alias_val; do
    if echo "$normalized" | grep -q "$alias_key" 2>/dev/null; then
      local alias_match=$(grep "|${alias_val}$" "$TMP_MAP" 2>/dev/null | head -1)
      if [ -n "$alias_match" ]; then
        echo "$alias_match"
        return 0
      fi
    fi
  done < "$TMP_ALIAS"

  # 1. Exakter Match auf normalisierten Namen
  local line=$(grep "^${normalized}|" "$TMP_MAP" 2>/dev/null | head -1)
  if [ -n "$line" ]; then
    echo "$line"
    return 0
  fi

  # 2. Fuzzy: EPG-Name enthält M3U-Namen oder umgekehrt
  while IFS='|' read -r norm_key tvg_id_orig display_name_orig; do
    if [[ "$norm_key" == *"$normalized"* || "$normalized" == *"$norm_key"* ]]; then
      echo "${norm_key}|${tvg_id_orig}|${display_name_orig}"
      return 0
    fi
  done < "$TMP_MAP"

  return 1
}

process_file() {
  local input="$1"
  local dir=$(dirname "$input")
  local base=$(basename "$input" .m3u)
  local output="${dir}/${base}.m3u"
  local tmp_out="${dir}/.${base}_tmp.m3u"
  local modified=0
  local matched=0
  local unmatched=0

  echo ""
  echo "=== $input ==="

  while IFS= read -r line; do
    if [[ "$line" =~ ^#EXTINF: ]]; then
      modified=$((modified + 1))
      # Channel-Name aus EXTINF extrahieren (nach letztem Komma)
      ch_name="${line##*,}"
      ch_clean=$(echo "$ch_name" | sed 's/[[:space:]]*$//')

      if map_result=$(map_channel "$ch_clean"); then
        tvg_id=$(echo "$map_result" | cut -d'|' -f2)
        tvg_name=$(echo "$map_result" | cut -d'|' -f3)
        echo "#EXTINF:0 tvg-id=\"$tvg_id\" tvg-name=\"$tvg_name\",$ch_clean" >> "$tmp_out"
        matched=$((matched + 1))
      else
        echo "#EXTINF:0,$ch_clean" >> "$tmp_out"
        echo "   ⚠ kein Match: $ch_clean"
        unmatched=$((unmatched + 1))
      fi
    else
      echo "$line" >> "$tmp_out"
    fi
  done < "$input"

  mv "$tmp_out" "$output"
  echo "   → $modified Zeilen, $matched gematcht, $unmatched nicht gefunden"
}

# Verarbeite übergebene Dateien oder alle aus m3u/
if [ $# -gt 0 ]; then
  for f in "$@"; do process_file "$f"; done
else
  for f in "$M3U_DIR"/*.m3u; do process_file "$f"; done
fi

echo ""
echo "=== Fertig ==="

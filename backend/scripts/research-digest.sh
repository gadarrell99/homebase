#!/bin/bash
cd ~/homebase/backend

# Run the scan
curl -s -X POST http://localhost:8000/api/research/scan > /dev/null

# Get summary
SUMMARY=$(curl -s http://localhost:8000/api/research/summary)
NEW_COUNT=$(echo $SUMMARY | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_items_24h',0))")

# Get high relevance items
ITEMS=$(curl -s 'http://localhost:8000/api/research?status=new&limit=10')

# Get email from config
EMAIL=$(curl -s http://localhost:8000/api/settings | python3 -c "import sys,json; print(json.load(sys.stdin).get('alert_email','artiedarrell@gmail.com'))")

# Send digest email
if [ "$NEW_COUNT" -gt 0 ]; then
  echo "Sending research digest to $EMAIL with $NEW_COUNT new items"
  
  # Format email body
  BODY="SENTINEL RESEARCH DIGEST - $(date -u +%Y-%m-%d)

NEW ITEMS FOUND: $NEW_COUNT

TOP FINDINGS:
$(echo $ITEMS | python3 -c "
import sys,json
items = json.load(sys.stdin)[:5]
for i,item in enumerate(items,1):
    print(f\"{i}. [{item.get('relevance_score',0)}] {item.get('title','')[:60]}\")
    print(f\"   {item.get('source','')} - {item.get('url','')}\")
    print()
")

View all: https://homebase.rize.bm/research
"

  echo "$BODY" | mail -s "[SENTINEL RESEARCH] Daily Digest - $NEW_COUNT new items" $EMAIL
fi

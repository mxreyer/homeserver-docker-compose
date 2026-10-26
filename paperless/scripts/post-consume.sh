#!/bin/bash
API="http://localhost:8000/api"
TOKEN="45c94dcd19be8cc42e106313d6575dc3a6ccf1c6"
AUTO_TAG_ID=12     # ID of paperless-gpt-auto (added to ALL documents)
OCR_TAG_ID=13      # ID of the paperless-gpt OCR tag (scanned documents only)
NATIVEPDF_TAG_ID=19 # ID of paperless-is-native-pdf (added to native pdf documents on import)
MIN_CHARS=50       # below this, treat the original as "no text layer"

add_tags() {
  curl -s -X POST \
    -H "Authorization: Token $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"documents\": [${DOCUMENT_ID}], \"method\": \"modify_tags\", \"parameters\": {\"add_tags\": [$1], \"remove_tags\": []}}" \
    "$API/documents/bulk_edit/"
}

chars=$(pdftotext -q "$DOCUMENT_SOURCE_PATH" - 2>/dev/null | tr -d '[:space:]' | wc -c)

# Native PDF with text: just add the auto tag, leave content alone
if [ "$chars" -ge "$MIN_CHARS" ]; then
  #add_tags "$AUTO_TAG_ID, $NATIVEPDF_TAG_ID"
  add_tags "$NATIVEPDF_TAG_ID"
  exit 0
fi

# Scanned/image: clear content, then add both tags in one call
curl -s -X PATCH \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": ""}' \
  "$API/documents/${DOCUMENT_ID}/"

#add_tags "$AUTO_TAG_ID, $OCR_TAG_ID"
add_tags "$OCR_TAG_ID"

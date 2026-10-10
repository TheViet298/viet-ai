"""Conservative text locations; relative positions are not dispatchable places."""
import re

LOCATION = re.compile(
    r"\b(?:(?:tại|ở)\s+)?(?P<station>trạm(?:\s+sạc)?|điểm\s+sạc)\s*(?P<name>[^,;.!?\n]{0,80})"
    r"|\b(?:tại|ở)\s+(?P<area>[^,;.!?\n]{1,80})", re.I,
)
CLAUSE_END = re.compile(r"\s+(?:nhưng|và|cắm|mã lỗi|lỗi|trụ|xe|đang|bị|không|vẫn)\b", re.I)
AMBIGUOUS = re.compile(
    r"^(?:đây|đó|đấy|này|kia|đâu|cạnh|bên|gần xe|gần nhà|một nơi|nơi|chỗ|"
    r"khu vực an toàn|vị trí an toàn|chế độ|trạng thái|mức pin|trụ|trạm|ở|tại)\b", re.I,
)
ADDRESS = re.compile(r"^(?:đường|phố|phường|quận|huyện|xã|tỉnh|thành phố|tp|km)\s+\S", re.I)
LANDMARK = re.compile(r"^(?:vincom|vinsmart|vinhomes|landmark|aeon|ecopark)\b", re.I)


def extract_locations(text: str) -> dict[str, str]:
    fields = {}
    for match in LOCATION.finditer(text):
        # A denied location is not a new observation.
        if re.search(r"(?:không|chưa|không còn)\s*$", text[max(0, match.start() - 20):match.start()], re.I):
            continue
        place = CLAUSE_END.split((match.group('name') if match.group('station') else match.group('area')).strip(), 1)[0].strip()
        if not place or AMBIGUOUS.search(place):
            continue
        lower = place.casefold()
        if lower in {'nhà', 'nhà tôi', 'nhà mình'}:
            if re.search(r'\bsạc\b', text, re.I):
                fields['station_location'] = 'Tại nhà'
            continue
        if re.search(r'\b(?:này|kia|đó|đây|gần đây|an toàn)\b', place, re.I):
            continue
        if match.group('station') or LANDMARK.search(place):
            fields['station_location'] = place
        elif ADDRESS.search(place) or sum(word[0].isupper() for word in place.split() if word) >= 2:
            fields['current_location'] = place
    return fields

"""Reviewed English presentation for the two compound service quick replies."""
import json
import re
from pathlib import Path


HELP_INPUTS = {
    'please explain public charging, charging fees and vinfast app features':
        'Hướng dẫn cách sạc pin tại trạm sạc công cộng, biểu phí sạc và tính năng trên App VinFast.',
    'i would like to ask about battery warranty and scheduled maintenance':
        'Tôi muốn hỏi chính sách bảo hành pin và lịch bảo dưỡng định kỳ.',
}

HELP_LABELS = {
    'Theo tài liệu VinFast:': 'According to VinFast documentation:',
    '### Cách sạc tại trạm công cộng': '### Charging at a public station',
    '### Biểu phí sạc': '### Charging fees',
    '### Tính năng trên App VinFast': '### VinFast app features',
    '### Bảo hành pin': '### Battery warranty',
    '### Bảo dưỡng định kỳ': '### Scheduled maintenance',
    'VinFast cung cấp đơn giá sạc ô tô điện, xe máy điện và hình thức thanh toán áp dụng tại các trạm sạc công cộng như sau:':
        'VinFast publishes the following charging rates and payment information for public stations:',
    'Phí sử dụng dịch vụ trạm sạc bổ sung sau khi hoàn thành phiên sạc:':
        'Additional station usage fees after the charging session has ended:',
    'Quý khách cho biết dòng xe, đời xe, số km hiện tại và xe có từng chạy dịch vụ hay không để em đối chiếu thời hạn bảo hành pin và lịch bảo dưỡng đúng xe nhé.':
        'Please provide your vehicle model, model year, current mileage and whether it has ever been used commercially so I can check the applicable battery warranty and maintenance schedule.',
    'Em chưa tìm được tài liệu chính thức đủ để xác nhận thông tin này. Quý khách có thể liên hệ chuyên viên VinFast để đối chiếu.':
        'I have not found enough official documentation to confirm this part. Please check with a VinFast specialist.',
    'Em chưa tra cứu được thông tin này. Quý khách vui lòng thử lại hoặc liên hệ chuyên viên VinFast để được hỗ trợ.':
        'I could not retrieve this information. Please try again or contact a VinFast specialist.',
}

HELP_CHIPS = {
    'Đặt hẹn bảo dưỡng': 'Book a maintenance appointment',
    'Chi phí bảo dưỡng định kỳ': 'Scheduled maintenance costs',
    'Danh sách xưởng dịch vụ': 'Service center list',
}

HELP_SOURCE_TITLES = {
    'SRC-010': 'VinFast public charging guide, section 2.1',
    'SRC-006': 'VinFast battery and charging services',
    'SRC-001': 'VinFast app user guide',
    'SRC-002': 'VinFast vehicle warranty policy',
    'SRC-004': 'VinFast maintenance services',
}


def english_help_answer(message: str) -> str | None:
    if not message.startswith('Theo tài liệu VinFast:') or '__HELP_' in message:
        return None
    fragments = {}
    def fragment(english):
        token = f'__HELP_{len(fragments)}__'
        fragments[token] = english
        return token
    translated = message
    root = Path(__file__).resolve().parents[2] / 'fixtures/knowledge'
    for name in ('charging_guides.json', 'warranty_maintenance.json'):
        for record in json.loads((root / name).read_text(encoding='utf-8')):
            if record['relevant_snippet'] in translated:
                translated = translated.replace(record['relevant_snippet'], fragment(record['relevant_snippet_en']))
    for original, english in HELP_LABELS.items():
        if original in translated:
            translated = translated.replace(original, fragment(english))
    # Match complete tariff lines, retaining every amount, tier and date.
    rules = [
        (r'Đơn giá sạc: ([\d.,]+) (?:VNĐ|VND)/kWh \(áp dụng từ ngày ([\d/]+)\)\.',
         r'Charging rate: \1 VND/kWh (effective from \2).'),
        (r'Miễn phí từ phút thứ (\d+) đến phút thứ (\d+)', r'Free from minute \1 to \2'),
        (r'([\d.,]+) đồng/phút từ phút thứ (\d+) đến phút thứ (\d+)', r'\1 VND/minute from minute \2 to \3'),
        (r'([\d.,]+) đồng/phút từ phút thứ (\d+) trở đi', r'\1 VND/minute from minute \2 onward'),
        (r'Đây là mức phí trong tài liệu đã xác minh ngày ([\d-]+)\. Cần kiểm tra biểu phí và ưu đãi áp dụng cho xe trên ứng dụng trước khi sạc\.',
         r'These rates are from documentation verified on \1. Check the app for the rates and promotions applicable to your vehicle before charging.'),
    ]
    lines = []
    for line in translated.split('\n'):
        prefix = '- ' if line.startswith('- ') else ''
        body = line.removeprefix(prefix) if prefix else line
        for pattern, replacement in rules:
            if re.fullmatch(pattern, body):
                english = re.sub(pattern, replacement, body)
                english = re.sub(r'\d{1,3}(?:\.\d{3})+(?= VND/)',
                                 lambda match: match[0].replace('.', ','), english)
                body = fragment(english)
                break
        lines.append(prefix + body)
    translated = '\n'.join(lines)
    # Unknown wording keeps the normal guarded translation path.
    if re.sub(r'__HELP_\d+__', '', translated).replace('- ', '').strip():
        return None
    for token, english in fragments.items():
        translated = translated.replace(token, english)
    return translated


def localize_help_response(data) -> bool:
    translated = english_help_answer(data.message) if not data.safe_guidance else None
    if (not translated or any(chip not in HELP_CHIPS for chip in data.suggested_replies or [])
            or any(c.source_id not in HELP_SOURCE_TITLES for c in data.citations or [])):
        return False
    data.message = translated
    data.suggested_replies = [HELP_CHIPS[chip] for chip in data.suggested_replies or []]
    for citation in data.citations or []:
        citation.title = HELP_SOURCE_TITLES.get(citation.source_id, citation.title)
    return True

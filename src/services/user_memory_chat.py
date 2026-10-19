"""Deterministic personal-memory intent and presentation; no generated facts."""
import re

from src.services.chat_normalization import fold_text
from src.services.user_memory import KEYS, MemorySnapshot, personal_memory_keys, resolve_personal_memory


def memory_mode(text: str, changes: list, snapshot: MemorySnapshot) -> str | None:
    body = fold_text(text)
    # Memory commands can accompany a real business/safety question. Those
    # continue through the ordinary handler and save only the explicit facts.
    domain = bool(re.search(r'bao hanh|bao duong|\bsac\b|huong dan|\bcach\b|\bgia\b|so sanh|adas|'
                            r'lai thu|test drive|appointment|booking|dat lich|ho so|cuu ho|warranty|maintenance|charging|\bcharge\b|\bhow\b|compare|\bprice\b|loi|smoke|fire|khoi|phanh', body))
    if changes and not domain:
        return 'write'
    recall = personal_memory_keys(text) and re.search(
        r'nhac lai|da (?:noi|khai bao|chon)|truoc|dong nao|mau xe nao|phien ban nao|o dau|'
        r'which|what|where|previous|remember about me|did i', body)
    if recall and not domain:
        return 'recall'
    if not domain and re.match(r'^(?:(?:hay|vui long|please)\s+)?(?:ghi nho|nho|remember)\b', body.strip()):
        return 'clarify'
    return None


def memory_reply(mode: str, snapshot: MemorySnapshot, language: str, *, text: str = '', keys=None, changes=(), result=None) -> str:
    english = language == 'en'
    if mode == 'guest':
        return ('Please sign in to save or recall personal information across chats.' if english else
                'Quý khách vui lòng đăng nhập để lưu hoặc nhắc lại thông tin cá nhân qua các phiên chat.')
    if mode == 'clarify':
        return ('Please identify the vehicle you own and the personal information you want saved.' if english else
                'Quý khách cho biết rõ xe đang sở hữu và thông tin cá nhân muốn em ghi nhớ nhé.')
    if mode == 'stale' or result and result.status == 'conflict':
        return ('Your saved information changed in another chat. I have not saved this change; please send it again if still needed.' if english else
                'Thông tin ghi nhớ đã thay đổi ở phiên khác. Em chưa lưu thay đổi này; Quý khách vui lòng gửi lại nếu vẫn muốn cập nhật.')
    if mode == 'write':
        forgotten = changes and all(change.status == 'retracted' for change in changes)
        if forgotten:
            return 'I have forgotten the personal information you requested.' if english else 'Em đã quên thông tin cá nhân theo yêu cầu của Quý khách.'
        return ('I have saved the personal information you explicitly allowed me to remember.' if english else
                'Em đã ghi nhớ thông tin cá nhân Quý khách cho phép lưu.')
    selected = (resolve_personal_memory(text, snapshot) if keys is None else
                {key: snapshot.facts[key].model_dump(mode='json') for key in keys
                 if key in KEYS and key in snapshot.facts and snapshot.facts[key].status == 'confirmed'})
    if not selected:
        return ('I do not have saved information for that question. You can tell me what you want remembered.' if english else
                'Em chưa có thông tin đã lưu để nhắc lại phần này. Quý khách có thể cho biết thông tin muốn em ghi nhớ.')
    labels = ({'owned_vehicle.model': 'Owned vehicle', 'owned_vehicle.version': 'Version',
        'owned_vehicle.model_year': 'Model year', 'owned_vehicle.battery_plan': 'Battery plan',
        'home_city': 'Home city', 'registration_city': 'Registration city'} if english else
        {'owned_vehicle.model': 'Xe sở hữu', 'owned_vehicle.version': 'Phiên bản',
         'owned_vehicle.model_year': 'Đời xe', 'owned_vehicle.battery_plan': 'Phương án pin',
         'home_city': 'Nơi ở', 'registration_city': 'Nơi đăng ký xe'})
    translated = {'Hà Nội': 'Hanoi', 'Đà Nẵng': 'Da Nang', 'TP. Hồ Chí Minh': 'Ho Chi Minh City',
                  'purchased': 'Purchased', 'subscription': 'Subscription'} if english else {
                  'purchased': 'mua kèm pin', 'subscription': 'thuê pin'}
    details = '; '.join(labels[key] + ': ' + str(translated.get(selected[key]['value'], selected[key]['value']))
                        for key in KEYS if key in selected)
    return ('You previously provided: ' if english else 'Quý khách đã cung cấp: ') + details + '.'

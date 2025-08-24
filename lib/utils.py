import json
import struct
from datetime import datetime, timezone
import logging

from lib.navtelecom import navtelecom


logging.basicConfig(level=logging.ERROR,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers = [
                        logging.FileHandler("server.log", encoding="utf-8"),  # запись в файл
                        logging.StreamHandler()  # дублирование в консоль
                    ])
logger = logging.getLogger(__name__)


def xor_sum(b: bytes) -> int:
    x = 0
    for bb in b:
        x ^= bb
    return x & 0xFF

def crc8(buffer: bytes) -> int:
    crc = 0xFF
    for b in buffer:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

def parse_ntc(packet: bytes):
    if len(packet) < 16 or packet[:4] != b'@NTC':
        raise ValueError('Не NTC пакет')
    id_obj = struct.unpack_from('<I', packet, 4)[0]
    id_dc = struct.unpack_from('<I', packet, 8)[0]
    size = struct.unpack_from('<H', packet, 12)[0]
    csd = packet[14]
    csp = packet[15]
    payload = packet[16:16+size]

    if xor_sum(payload) != csd:
        logger.error('В NTC пакете не совпадает контрольная сумма данных (csd)')
        raise ValueError(f'CSD не совпадает')
    if xor_sum(packet[:15]) != csp:
        logger.error('В NTC пакете не совпадает контрольная сумма заголовка (csp)')
        raise ValueError('CSP не совпадает')

    return id_obj, id_dc, payload

def make_ntc_reply(payload: bytes,id_dc: int, id_obj: int) -> bytes:
    head = b'@NTC' + struct.pack('<I', id_obj) + struct.pack('<I', id_dc) + struct.pack('<H', len(payload))
    csd = xor_sum(payload)
    first15 = head + bytes([csd]) # первые 15 байт заголовка
    csp = xor_sum(first15[:15]) # csp по первым 15 байтам
    return first15 + bytes([csp]) + payload


async def handle_flex_agreement(writer, packet: bytes):
    id_obj, id_dc, payload = parse_ntc(packet)

    if not payload.startswith(b'*>FLEX'):
        return False

    protocol = payload[6] # 0xb0
    protocol_ver = payload[7] # Для версии 1.0 - 10 (0x0A)
                              # Для версии 2.0 - 20 (0x14)
                              # Для версии 3.0 - 30 (0x1E)
    struct_ver = payload[8]  # здесь также

    if protocol_ver == 10 and struct_ver == 10:
        navtelecom.version = 1

    elif protocol_ver == 20 and struct_ver == 20:
        navtelecom.version = 2

    elif protocol_ver == 30 and struct_ver == 30:
        navtelecom.version = 3

    else:
        logger.error(f'Версия протокола ({protocol_ver/10}) и версия структуры ({struct_ver/10}) различаются')
        raise ValueError(f'Версия протокола ({protocol_ver/10}) и версия структуры ({struct_ver/10}) различаются')


    reply_payload = b'*<FLEX' + bytes([0xB0, protocol_ver, struct_ver])
    reply_packet  = make_ntc_reply(reply_payload, id_obj, id_dc)

    writer.write(reply_packet)
    await writer.drain()

    navtelecom.device_id = id_dc
    return True

def parse_flex_packet(data: bytes):
    if not data.startswith(b'~C'):
        logger.error("Некорректный пакет: нет преамбулы ~C")
        raise ValueError("Некорректный пакет: нет преамбулы ~C")


    if len(data) < 29:
        logger.error("Payload слишком короткий ДАЖЕ для FLEX 1.0")
        raise ValueError("Payload слишком короткий ДАЖЕ для FLEX 1.0")

    numPage, code, timestamp, last_time, latitude, longitude, speed = struct.unpack(
        '<I H I I i i f', data[2:28])

    latitude /= 1_000_000
    longitude /= 1_000_000

    result = {
        "numPage": numPage,
        "code": code,
        "timestamp": datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "last_time": datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "speed": speed
    }
    return result
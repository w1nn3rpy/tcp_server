import asyncio
import json

from lib.navtelecom import navtelecom
from lib.utils import parse_ntc, parse_flex_packet, make_ntc_reply, handle_flex_agreement, crc8


async def auth(writer: asyncio.StreamWriter, data: bytes):
    # отправляем согласование FLEX
    id_dc, id_obj, payload = parse_ntc(data)
    handshake = make_ntc_reply(b"*<S", id_dc, id_obj)
    writer.write(handshake)
    await writer.drain()

async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):

    while True:
        try:
            data = await reader.read(1024)
            if not data:
                break

            if data.startswith(b'@NTC') and not b'*>FLEX' in data:
                await auth(writer, data)

            elif data.startswith(b'@NTC') and b'*>FLEX' in data:
                await handle_flex_agreement(writer, data)

            elif data.startswith(b"~C"):
                device_id = navtelecom.device_id
                result = {'device_id': device_id, }


                for i, k in parse_flex_packet(data).items():
                    result[i] = k

                print(json.dumps(result, indent=4))

                # формирование ответа на ~C
                start = bytes(data[:2])
                response_crc = crc8(start)
                response = start + bytes([response_crc])
                writer.write(response)
                await writer.drain()
            else:
                print('Получен пакет:', data)

        except (ConnectionResetError, asyncio.IncompleteReadError):
            print(f"Клиент закрыл соединение")
            break
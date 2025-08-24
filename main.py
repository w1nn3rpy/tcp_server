import asyncio

async def main():
    from handlers import handler

    server = await asyncio.start_server(handler, "0.0.0.0", 9000)
    async with server:
        print("Сервер слушает порт 9000")
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

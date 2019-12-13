import asyncio
from aiohttp import web
import datetime
import aiofiles
import os
import logging

INTERVAL_SECS = 1
ARCHIVE_FOLDER = 'test_photos'
CHUNK_SIZE = 10


async def archivate(request):
    response = web.StreamResponse()

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment'

    # Отправляет клиенту HTTP заголовки
    await response.prepare(request)
    archive_hash = request.match_info['archive_hash']
    archive_path = os.path.join(ARCHIVE_FOLDER, archive_hash)
    if not os.path.isdir(archive_path):
        raise web.HTTPNotFound(text='Archive not found')
    proc = await asyncio.create_subprocess_shell(
        'zip -r - {}'.format(archive_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    while True:
        archive_chunk = await proc.stdout.read(CHUNK_SIZE)
        logging.debug('Sending archive chunk')
        await response.write(archive_chunk)
        if not archive_chunk:
            break
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate)
    ])
    web.run_app(app)

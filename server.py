import asyncio
from aiohttp import web
import datetime
import aiofiles
import os
import logging
import argparse
from functools import partial

CHUNK_SIZE = 1000


async def archivate(request, photos_folder, download_delay):
    response = web.StreamResponse()

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment'

    # Отправляет клиенту HTTP заголовки
    await response.prepare(request)
    archive_hash = request.match_info['archive_hash']
    archive_path = os.path.join(photos_folder, archive_hash)
    if not os.path.isdir(archive_path):
        raise web.HTTPNotFound(text='Archive not found')
    archiving_proc = await asyncio.create_subprocess_shell(
        'zip -r - {}'.format(archive_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    try:
        while True:
            logging.debug('Sending archive chunk')
            archive_chunk = await archiving_proc.stdout.read(CHUNK_SIZE)
            if not archive_chunk:
                break
            await response.write(archive_chunk)
            await asyncio.sleep(download_delay)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        raise
    finally:
        response.force_close()
        if archiving_proc.returncode is None:
            archiving_proc.kill()
            logging.debug('Process killed')
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Photo downloading microservice')
    parser.add_argument('--logging',
                        default='on',
                        type=str,
                        help='Shows the debug messages')
    parser.add_argument('--photos_folder',
                        default='test_photos',
                        type=str,
                        help='Path to the folder with photos')
    parser.add_argument('--delay',
                        default=0,
                        type=int,
                        help='Number of seconds to delay the downloading of each archive chunk')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    if args.logging != 'on':
        logging.basicConfig(level=logging.CRITICAL)
    download_delay = args.delay
    photos_folder = args.photos_folder
    archivate_partial = partial(
        archivate,
        photos_folder=photos_folder,
        download_delay=download_delay
    )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate_partial)
    ])
    web.run_app(app)

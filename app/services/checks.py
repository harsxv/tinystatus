import aiohttp
import asyncio
import subprocess
import platform
import logging
from typing import Optional

PLATFORM = platform.system().lower()

async def check_http(url: str, expected_code: int, selfsigned: bool = False) -> bool:
    timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, ssl=not selfsigned) as response:
                return response.status == expected_code
    except Exception as err:
        logging.error(f"Error checking {url}: {err}")
        return False

async def check_ping(host: str) -> bool:
    try:
        # Use asyncio.create_subprocess_exec for better performance
        if PLATFORM == 'windows':
            process = await asyncio.create_subprocess_exec(
                'ping', '-n', '1', '-w', '2000', host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '2', host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        
        await process.communicate()
        return process.returncode == 0
    except Exception as e:
        logging.error(f"Error pinging {host}: {e}")
        return False

async def check_port(host: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0  # 5 second timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception as e:
        logging.error(f"Error checking port {host}:{port}: {e}")
        return False 
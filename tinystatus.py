import os
import time

from dotenv import load_dotenv
import yaml
import asyncio
import aiohttp
import subprocess
import markdown
from jinja2 import Template
from datetime import datetime
import json
import logging
import platform

# Load environment variables
load_dotenv()

# Configuration
MONITOR_CONTINOUSLY = os.getenv('MONITOR_CONTINOUSLY', 'True') == 'True'
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 30))
MAX_HISTORY_ENTRIES = int(os.getenv('MAX_HISTORY_ENTRIES', 100))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
CHECKS_FILE = os.getenv('CHECKS_FILE', 'checks.yaml')
INCIDENTS_FILE = os.getenv('INCIDENTS_FILE', 'incidents.md')
TEMPLATE_FILE = os.getenv('TEMPLATE_FILE', 'index.html.theme')
HISTORY_TEMPLATE_FILE = os.getenv('HISTORY_TEMPLATE_FILE', 'history.html.theme')
STATUS_HISTORY_FILE = os.getenv('STATUS_HISTORY_FILE', 'history.json')
HTML_OUTPUT_DIRECTORY = os.getenv('HTML_OUTPUT_DIRECTORY', os.getcwd())

# Platform Idendifier
PLATFORM = platform.system().lower()

# Service check functions
async def check_http(url, expected_code, selfsigned):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, ssl=not selfsigned) as response:
                return response.status == expected_code
        except Exception as err:
            print("error with ", url, err)
            return False


async def check_ping(host):
    try:
        if PLATFORM == 'windows':
            result = subprocess.run(['ping', '-n', '1', '-w', '2000', host], capture_output=True, text=True)
        else:
            result = subprocess.run(['ping', '-c', '1', '-W', '2', host], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False


async def check_port(host, port):
    try:
        _, writer = await asyncio.open_connection(host, port)
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False


async def run_checks(checks):
    background_tasks = {}
    async with asyncio.TaskGroup() as tg:
        for check in checks:
            if check['type'] == 'http':
                if 'ssc' in check:
                    selfcert = check['ssc']
                else:
                    selfcert = False

            task = tg.create_task(
                check_http(check['host'], check['expected_code'], selfcert) if check['type'] == 'http' else
                check_ping(check['host']) if check['type'] == 'ping' else
                check_port(check['host'], check['port']) if check['type'] == 'port' else None,
                name=check['name']
            )
            if task:
                background_tasks[check['name']] = task

    results = [
        {
            "name": check["name"],
            "url": check.get("url"),
            "status": background_tasks[check["name"]].result()}
        for check in checks
    ]

    return results


# History management
def load_history():
    if os.path.exists(STATUS_HISTORY_FILE):
        with open(STATUS_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(STATUS_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def update_history(results):
    # TODO: Configure groups in history page
    history = load_history()
    current_time = datetime.now().isoformat()
    for group in results.keys():
        for check in results[group]:
            if check['name'] not in history:
                history[check['name']] = []
            history[check['name']].append({'timestamp': current_time, 'status': check['status']})
            history[check['name']] = history[check['name']][-MAX_HISTORY_ENTRIES:]
    save_history(history)


# Main monitoring loop
async def monitor_services():
    os.makedirs(HTML_OUTPUT_DIRECTORY, exist_ok=True)

    while True:
        start_ts = time.monotonic()
        down_services = []
        try:
            with open(CHECKS_FILE, 'r') as f:
                groups = yaml.safe_load(f)

            with open(INCIDENTS_FILE, 'r') as f:
                incidents = markdown.markdown(f.read())

            with open(TEMPLATE_FILE, 'r') as f:
                template = Template(f.read())

            with open(HISTORY_TEMPLATE_FILE, 'r') as f:
                history_template = Template(f.read())

            results = {}
            for group in groups:
                results[group['title']] = await run_checks(group['checks'])

            update_history(results)

            html = template.render(groups=results, incidents=incidents, last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            with open(os.path.join(HTML_OUTPUT_DIRECTORY, 'index.html'), 'w') as f:
                f.write(html)

            history_html = history_template.render(history=load_history(), last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            with open(os.path.join(HTML_OUTPUT_DIRECTORY, 'history.html'), 'w') as f:
                f.write(history_html)

            logging.info(f"Status page and history updated at {datetime.now()}")

            for group in results:
                group_down = [check['name'] for check in results[group] if not check['status']]
                down_services += group_down

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")

        # down_services = [group[check]['name'] for check in group in results if not check['status']]
        if down_services:
            logging.warning(f"Services currently down: {', '.join(down_services)}")

        if not MONITOR_CONTINOUSLY:
            return
        time_spent = int(time.monotonic() - start_ts)
        await asyncio.sleep(max(0, CHECK_INTERVAL - time_spent))


# Main function
def main():
    with open(CHECKS_FILE, 'r') as f:
        checks = yaml.safe_load(f)

    with open(INCIDENTS_FILE, 'r') as f:
        incidents = markdown.markdown(f.read())

    with open(TEMPLATE_FILE, 'r') as f:
        template = Template(f.read())

    results = asyncio.run(run_checks(checks))
    html = template.render(checks=results, incidents=incidents, last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    os.makedirs(HTML_OUTPUT_DIRECTORY, exist_ok=True)
    with open(os.path.join(HTML_OUTPUT_DIRECTORY, 'index.html'), 'w') as f:
        f.write(html)

if __name__ == "__main__":
    logging.basicConfig(level=getattr(logging, LOG_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(monitor_services())

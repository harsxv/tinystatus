# TinyStatus

TinyStatus is a simple, customizable status page generator that allows you to monitor the status of various services and display them on a clean, responsive web page. [Check out an online demo.](https://status.harry.id)

## Features

- Monitor HTTP endpoints, ping hosts, and check open ports
- Responsive design for both status page and history page
- Customizable service checks via YAML configuration
- Incident history tracking
- Automatic status updates at configurable intervals

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

## Installation

1. Clone the repository or download the source code:
   ```
   git clone https://github.com/yourusername/tinystatus.git
   cd tinystatus
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project root and customize the variables:
   ```
   CHECK_INTERVAL=30
   MAX_HISTORY_ENTRIES=100
   LOG_LEVEL=INFO
   CHECKS_FILE=checks.yaml
   INCIDENTS_FILE=incidents.md
   TEMPLATE_FILE=index.html.theme
   HISTORY_TEMPLATE_FILE=history.html.theme
   STATUS_HISTORY_FILE=history.json
   ```

2. Edit the `checks.yaml` file to add or modify the services you want to monitor. Example:
   ```yaml
   - name: GitHub Home
     type: http
     host: https://github.com
     expected_code: 200

   - name: Google DNS
     type: ping
     host: 8.8.8.8

   - name: Database
     type: port
     host: db.example.com
     port: 5432
   ```

3. (Optional) Customize the `incidents.md` file to add any known incidents or maintenance schedules.

4. (Optional) Modify the `index.html.theme` and `history.html.theme` files to customize the look and feel of your status pages.

## Usage

1. Run the TinyStatus script:
   ```
   python tinystatus.py
   ```

2. The script will generate two HTML files:
   - `index.html`: The main status page
   - `history.html`: The status history page

3. To keep the status page continuously updated, you can run the script in the background:
   - On Unix-like systems (Linux, macOS):
     ```
     nohup python tinystatus.py &
     ```
   - On Windows, you can use the Task Scheduler to run the script at startup.

4. Serve the generated HTML files using your preferred web server (e.g., Apache, Nginx, or a simple Python HTTP server for testing).

## Customization

- Adjust the configuration variables in the `.env` file to customize the behavior of TinyStatus.
- Customize the appearance of the status page by editing the CSS in `index.html.theme` and `history.html.theme`.
- Add or remove services by modifying the `checks.yaml` file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

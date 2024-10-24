<div align="center" width="100%">
    <img src="./assets/android-chrome-192x192.png" width="128" alt="" />
</div>

# TinyStatus
TinyStatus is a simple, customizable status page generator that allows you to monitor the status of various services and display them on a clean, responsive web page.

Check out an online demo https://status.harry.id

| Light Mode | Dark Mode | 
|-|-|
| ![Light](https://github.com/user-attachments/assets/3ea7b55e-397f-4f7c-8189-64b74a03594b) | ![Dark](https://github.com/user-attachments/assets/92072f9e-1031-4f07-8392-1111df57453a) |


## Features

- Monitor HTTP endpoints, ping hosts, and check open ports
- Responsive design for both status page and history page
- Customizable service checks via YAML configuration
- Incident history tracking
- Automatic status updates at configurable intervals
- Supports both light and dark themes
- Supports grouping
- Cards clickable (optional)

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## Installation

1. Clone the repository or download the source code:
   ```
   git clone https://github.com/harsxv/tinystatus.git
   cd tinystatus
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project root and customize the variables:
   ```
   MONITOR_CONTINOUSLY=True
   CHECK_INTERVAL=30
   MAX_HISTORY_ENTRIES=100
   LOG_LEVEL=INFO
   CHECKS_FILE=checks.yaml
   INCIDENTS_FILE=incidents.md
   TEMPLATE_FILE=index.html.theme
   HISTORY_TEMPLATE_FILE=history.html.theme
   STATUS_HISTORY_FILE=history.json
   HTML_OUTPUT_DIRECTORY=/var/www/htdocs/status/
   ```

2. Edit the `checks.yaml` file to add or modify the services you want to monitor.
   Example:
   ```yaml
    - title: 'Group 1'
      checks:
        - name: GitHub Home
          type: http
          host: https://github.com
          url: https://docs.github.com/en
          expected_code: 200

        - name: Google Public DNS
          type: ping
          host: 8.8.8.8

        - name: Dummy MySQL Database
          type: port
          host: db.example.com
          port: 3306

       - name: Home Server with Self-Signed Certs
          type: http
          host: https://homeserver.local
          ssc: True
          expected_code: 200
   ```

3. (Optional) Customize the `incidents.md` file to add any known incidents or maintenance schedules.

4. (Optional) Modify the `index.html.theme` and `history.html.theme` files to customize the look and feel of your status pages.

## Usage

1. Run the TinyStatus script:
   ```
   python tinystatus.py
   ```

2. The script will generate three files:
   - `index.html`: The main status page
   - `history.html`: The status history page
   - `history.json`: The status history and timestamp data

3. To keep the status page continuously updated, you can run the script in the background:
   - On Unix-like systems (Linux, macOS):
     ```
     nohup python tinystatus.py &
     ```
   - On Windows, you can use the Task Scheduler to run the script at startup.

4. Serve the generated HTML files using your preferred web server (e.g., Apache, NGINX, or a simple Python HTTP server for testing).

## Using Docker

In order to run the script using Docker:

   ```
    docker build -t tinystatus .
    docker run -ti --rm --name tinystatus -v "$PWD":/usr/src/myapp -w /usr/src/myapp tinystatus
   ```

## Customization

- Adjust the configuration variables in the `.env` file to customize the behavior of TinyStatus.
- Customize the appearance of the status page by editing the CSS in `index.html.theme` and `history.html.theme`.
- Add or remove services by modifying the `checks.yaml` file.

## Porting TinyStatus

TinyStatus porting are available in:
- Go: https://github.com/annihilatorrrr/gotinystatus

## Contributing

[Contributions](https://github.com/harsxv/tinystatus/contribute) are, of course, most welcome!

## License

This project is open source and available under the [MIT License](LICENSE).

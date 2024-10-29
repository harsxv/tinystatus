FROM python:3.12-alpine 

# Set the working directory
WORKDIR /usr/src/app

# Copy the necessary files into the container
COPY checks.yaml \
     history.html.theme \
     incidents.md \
     index.html.theme \
     requirements.txt \
     tinystatus.py ./

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 for the HTTP server
EXPOSE 8080

# Run the monitoring script in the background and start the HTTP server
CMD ["sh", "-c", "python tinystatus.py & python -m http.server 8080 --directory ."]

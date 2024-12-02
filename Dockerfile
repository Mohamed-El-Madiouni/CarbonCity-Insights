# Base Python image
FROM python:3.9

# Set working directory inside the container
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install cron
RUN apt-get update && apt-get install -y cron

# Copy the cron job file into the cron directory
COPY vehicle_cron /etc/cron.d/vehicle_cron

# Set permissions for the cron job file
RUN chmod 0644 /etc/cron.d/vehicle_cron

# Apply the cron job to the system's crontab
RUN crontab /etc/cron.d/vehicle_cron

# Create a directory for logs
RUN mkdir -p /app/log

# Set permissions
RUN chmod -R 777 /app/log
RUN touch /app/log/vehicle_cron.log
RUN chmod 666 /app/log/vehicle_cron.log

RUN crontab -l
RUN date

# Start cron in the foreground
CMD ["python", "/app/app/services/vehicle_data_service.py"]


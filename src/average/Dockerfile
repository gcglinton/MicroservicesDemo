# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the Python requirements file
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Kafka Sum microservice files to the container
COPY average.py .

# Set the entrypoint command to run the Kafka Sum microservice
CMD ["python", "average.py"]

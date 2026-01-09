# dockerfile for mock blackvue dashcam server
FROM python:3.9-alpine

# installs required packages
RUN pip install --no-cache-dir Flask~=3.1 requests~=2.32

# creates app directory
WORKDIR /app

# copies features directory structure to match import paths
COPY features/ /app/features/

# exposes flask port
EXPOSE 5000

# runs mock dashcam server
CMD ["python", "/app/features/mock_dashcam/entrypoint.py"]

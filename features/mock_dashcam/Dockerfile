# dockerfile for the mock BlackVue dashcam server
FROM python:3.9-alpine

RUN pip install --no-cache-dir Flask~=3.1

WORKDIR /app

# copies the modules the server imports, keeping their package paths
COPY features/__init__.py /app/features/
COPY features/lib/__init__.py features/lib/recordings.py /app/features/lib/
COPY features/mock_dashcam/__init__.py features/mock_dashcam/entrypoint.py \
     features/mock_dashcam/server.py /app/features/mock_dashcam/
COPY features/mock_dashcam/files/ /app/features/mock_dashcam/files/

# matches MOCK_DASHCAM_PORT in server.py
EXPOSE 5000

CMD ["python", "-m", "features.mock_dashcam.entrypoint"]

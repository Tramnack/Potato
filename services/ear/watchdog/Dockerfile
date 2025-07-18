# services/ear/watchdog/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 1. Create the necessary directory structure inside the container for the app.
# This ensures that when we COPY files into /app/services/ear/ and /app/services/shared_libs,
# those target directories already exist and are treated as Python packages.
RUN mkdir -p /app/services/ear/watchdog \
           /app/services/shared_libs \
           /app/services/ear

# 2. Copy the contents of THIS specific service implementation into its destination.
# `COPY .` here means "copy everything from the build context" (i.e., everything in services/ear/watchdog)
# into `/app/services/ear/watchdog` inside the container.
COPY ear/watchdog /app/services/ear/watchdog/

# 3. Copy the abstract base class for Ear.
# It's one level up from the build context (services/ear/watchdog -> services/ear/)
COPY ear/abstract_ear.py /app/services/ear/abstract_ear.py

# 4. Copy the shared_libs.
# It's two levels up (services/ear/watchdog -> services/ear -> services/) then into shared_libs
COPY shared_libs /app/services/shared_libs

# 5. Install Python dependencies specific to this service.
# The requirements.txt file was copied with the service's own files in step 2.
RUN pip install --no-cache-dir -r /app/services/shared_libs/requirements.txt
RUN pip install --no-cache-dir -r /app/services/ear/watchdog/requirements.txt

# 6. Set PYTHONPATH so Python can find the 'services' package from the root of '/app'.
ENV PYTHONPATH=/app:$PYTHONPATH

# 7. Define the command to run the application.
# Provide the full path to app.py relative to the container's root.
CMD ["python", "/app/services/ear/watchdog/app.py"]
# services/brain/echo/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 1. Create the necessary directory structure inside the container for the app.
# This ensures that when we COPY files into /app/services/brain/ and /app/services/shared_libs,
# those target directories already exist and are treated as Python packages.
RUN mkdir -p /app/services/brain/echo \
           /app/services/shared_libs \
           /app/services/brain

# 2. Copy the contents of THIS specific service implementation into its destination.
# `COPY .` here means "copy everything from the build context" (i.e., everything in services/brain/echo)
# into `/app/services/brain/echo` inside the container.
COPY brain/echo /app/services/brain/echo/

# 3. Copy the abstract base class for Ear.
# It's one level up from the build context (services/brain/echo -> services/brain/)
COPY brain/abstract_brain.py /app/services/brain/abstract_brain.py

# 4. Copy the shared_libs.
# It's two levels up (services/brain/echo -> services/brain -> services/) then into shared_libs
COPY shared_libs /app/services/shared_libs

# 5. Install Python dependencies specific to this service.
# The requirements.txt file was copied with the service's own files in step 2.
RUN pip install --no-cache-dir -r /app/services/shared_libs/requirements.txt
RUN pip install --no-cache-dir -r /app/services/brain/echo/requirements.txt

# 6. Set PYTHONPATH so Python can find the 'services' package from the root of '/app'.
ENV PYTHONPATH=/app:$PYTHONPATH

# 7. Define the command to run the application.
# Provide the full path to app.py relative to the container's root.
CMD ["python", "/app/services/brain/echo/app.py"]
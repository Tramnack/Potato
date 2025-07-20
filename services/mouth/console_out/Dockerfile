# services/mouth/console_out/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 1. Create the necessary directory structure inside the container for the app.
# This ensures that when we COPY files into /app/services/mouth/ and /app/services/shared_libs,
# those target directories already exist and are treated as Python packages.
RUN mkdir -p /app/services/mouth/console_out \
           /app/services/shared_libs \
           /app/services/mouth

# 2. Copy the contents of THIS specific service implementation (console_out) into its destination.
# `COPY .` here means "copy everything from the build context" (i.e., everything in services/mouth/console_out)
# into `/app/services/mouth/console_out` inside the container.
COPY mouth/console_out /app/services/mouth/console_out/

# 3. Copy the abstract base class for mouth.
# It's one level up from the build context (services/mouth/console_out -> services/mouth/)
COPY mouth/abstract_mouth.py /app/services/mouth/abstract_mouth.py

# 4. Copy the shared_libs.
# It's two levels up (services/mouth/console_out -> services/mouth -> services/) then into shared_libs
COPY shared_libs /app/services/shared_libs

# 5. Install Python dependencies specific to this service.
# The requirements.txt file was copied with the service's own files in step 2.
RUN pip install --no-cache-dir -r /app/services/shared_libs/requirements.txt
RUN pip install --no-cache-dir -r /app/services/mouth/console_out/requirements.txt

# 6. Set PYTHONPATH so Python can find the 'services' package from the root of '/app'.
ENV PYTHONPATH=/app:$PYTHONPATH

# 7. Define the command to run the application.
# Provide the full path to app.py relative to the container's root.
CMD ["python", "/app/services/mouth/console_out/app.py"]
# services/template/specific/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 1. Create the necessary directory structure inside the container for the app.
# This ensures that when we COPY files into /app/services/template/ and /app/services/shared_libs,
# those target directories already exist and are treated as Python packages.
RUN mkdir -p /app/services/template/specific \
           /app/services/shared_libs \
           /app/services/template

# 2. Copy the contents of THIS specific service implementation (specific) into its destination.
# `COPY .` here means "copy everything from the build context" (i.e., everything in services/template/specific)
# into `/app/services/template/specific` inside the container.
COPY template/specific /app/services/template/specific/

# 3. Copy the abstract base class for template.
# It's one level up from the build context (services/template/specific -> services/template/)
COPY template/abstract_template.py /app/services/template/abstract_template.py

# 4. Copy the shared_libs.
# It's two levels up (services/template/specific -> services/template -> services/) then into shared_libs
COPY shared_libs /app/services/shared_libs
COPY ../shared_libs /app/shared_libs

# 5. Install Python dependencies specific to this service.
# The requirements.txt file was copied with the service's own files in step 2.
RUN pip install --no-cache-dir -r /app/services/shared_libs/requirements.txt
RUN pip install --no-cache-dir -r /app/services/template/specific/requirements.txt

# 6. Set PYTHONPATH so Python can find the 'services' package from the root of '/app'.
ENV PYTHONPATH=/app:$PYTHONPATH

# 7. Define the command to run the application.
# Provide the full path to app.py relative to the container's root.
CMD ["python", "/app/services/template/specific/app.py"]
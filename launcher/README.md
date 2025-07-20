Develop `potato_launcher.py`:

Implement the logic: load config, prompt user, save selection, generate (or heavily modify) a `docker-compose.yml` file,
and then call `docker compose up`.

The `services_config.yaml` will store the paths to the `Dockerfiles` (e.g., `build: ./services/ear/mic-input`) and other
specific configurations for each service variant.
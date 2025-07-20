"""
Potato Launcher: A tool for selecting and launching service configurations
with Docker Compose.

This script allows users to select implementations for a set of services,
either from a predefined preset or through manual selection. It then generates
a docker-compose.yml file, starts the services, and performs health checks.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any

import inquirer
import yaml
from jinja2 import Template

from health_check.health_check import check_urls_in_parallel

# --- Constants ---
CONFIG_FILE = Path("services_config.yaml")
PRESETS_DIR = Path("Presets")
USER_SELECTION_FILE = Path("user_selection.yaml")
DOCKER_COMPOSE_FILE = Path("docker-compose.yml")
DOCKER_COMPOSE_TEMPLATE = Path("templates/potato-launcher-compose.yml.jinja")


# --- Data Classes for Configuration ---


@dataclass
class HealthCheckConfig:
    """Configuration for a service health check."""
    port: int
    path: str
    interval: int = 5  # seconds
    attempts: int = 5


@dataclass
class ImplementationConfig:
    """
    Configuration for a specific implementation of a service.

    :param name: The unique name of this implementation.
    :param service: The name of the service this implementation belongs to.
    :param docker_service_name: The name to use for the service in docker-compose.
    :param description: A human-readable description.
    :param image: The Docker image to use.
    :param container_name: Optional explicit name for the Docker container.
    :param environment: Environment variables to set for the container.
    :param volumes: A list of volume mappings.
    :param ports: A list of port mappings.
    :param health_check: Optional health check configuration.
    :param depends_on: A list of services this implementation depends on.
    """
    name: str
    service: str
    docker_service_name: str
    description: str
    image: str
    container_name: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    volumes: Optional[List[str]] = None
    ports: Optional[List[str]] = None
    health_check: Optional[HealthCheckConfig] = None
    depends_on: Optional[List[str]] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.ports:
            for port in self.ports:
                if ":" not in port:
                    raise ValueError(f"Invalid port mapping: {port}")

        if self.health_check:
            if not self.ports:
                raise ValueError(
                    f"Implementation '{self.name}' has a health_check but no ports defined."
                )
            for port in self.ports:
                if self.health_check.port == int(port.split(":")[0]):
                    break
            else:
                raise ValueError(
                    f"Health check port {self.health_check.port} for '{self.name}' "
                    "is not listed in its exposed ports."
                )


@dataclass
class ServiceConfig:
    """
    Represents a service that can have multiple implementations.

    :param name: The name of the service (e.g., 'database', 'api').
    :param description: A human-readable description of the service's role.
    :param implementations: A dictionary mapping implementation names to their configs.
    """
    name: str
    description: str
    implementations: Dict[str, ImplementationConfig]


# --- Configuration Loading ---


def load_yaml_file(file_path: Path) -> Optional[dict]:
    """A generic utility to load a YAML file."""
    if not file_path.exists():
        return None
    with open(file_path) as f:
        return yaml.safe_load(f)


def save_yaml_file(file_path: Path, data: dict):
    """A generic utility to save data to a YAML file."""
    with open(file_path, "w") as f:
        yaml.dump(data, f)


def load_text_file(file_path: Path) -> str:
    """A generic utility to load text data from a file."""
    with open(file_path) as f:
        return f.read()


def save_text_file(file_path: Path, data: str):
    """A generic utility to save text data to a file."""
    with open(file_path, "w") as f:
        f.write(data)


def load_services_config(file_path: Path) -> Dict[str, ServiceConfig]:
    """
    Loads and parses the main services configuration file.

    :param file_path: The path to the services YAML configuration file.
    :returns: A dictionary mapping service names to ServiceConfig objects.
    """
    print(f"Loading services configuration from '{file_path}'...")
    config_data = load_yaml_file(file_path)

    if not config_data:
        raise ValueError(f"Failed to load services configuration from '{file_path}'")

    services = {}
    for service_type, service_data in config_data.items():
        service_name = service_data.get("name", service_type)
        raw_implementations = service_data.get("implementations", [])

        implementations = {}
        for impl_data in raw_implementations:
            # If a health_check dict is present, convert it to a HealthCheckConfig object
            if "health_check" in impl_data and isinstance(impl_data["health_check"], dict):
                impl_data["health_check"] = HealthCheckConfig(**impl_data["health_check"])

            # Create the ImplementationConfig object
            impl = ImplementationConfig(**impl_data, service=service_name)
            implementations[impl.name] = impl

        services[service_name] = ServiceConfig(
            name=service_name,
            description=service_data["description"],
            implementations=implementations,
        )
    print("Configuration loaded successfully.")
    return services


# --- User Interaction and Selection Logic ---

def select_implementations(services: Dict[str, ServiceConfig]) -> Dict[str, ImplementationConfig]:
    """
    Guides the user through selecting an implementation for each service.

    This function first checks for presets and allows the user to select one.
    If no preset is chosen, it falls back to manual selection for each service.

    :param services: The dictionary of available services and their implementations.

    :returns: A dictionary mapping service names to the selected ImplementationConfig.
    """
    # 1. Try to select from a preset
    preset_implementations = _select_from_preset(services)
    if preset_implementations is not None:
        return preset_implementations

    # 2. Fallback to manual selection
    print("No preset selected. Proceeding with manual selection...")
    return _select_manually(services)


def _select_from_preset(services: Dict[str, ServiceConfig]) -> Optional[Dict[str, ImplementationConfig]]:
    """
    Prompts the user to select a preset and loads its configuration.

    :returns: The selected implementations if a preset is chosen, otherwise None.
    """
    presets = list(PRESETS_DIR.glob("*.yaml"))
    if not presets:
        return None

    questions = [
        inquirer.List(
            "preset",
            message="A preset defines a pre-selected set of services. Select one or choose 'None' for manual setup",
            choices=[None] + [p.stem for p in presets]
        )
    ]
    answers = inquirer.prompt(questions)
    selected_preset_name = answers["preset"]

    if not selected_preset_name:
        return None

    print(f"Loading preset: '{selected_preset_name}'...")
    preset_path = PRESETS_DIR / f"{selected_preset_name}.yaml"
    preset_data = load_yaml_file(preset_path)

    selected_implementations = {}
    for service_name, impl_name in preset_data.items():
        service = services.get(service_name)
        if not service:
            print(f"Warning: Service '{service_name}' from preset not found in main config. Skipping.")
            continue

        implementation = service.implementations.get(impl_name)
        if not implementation:
            print(f"Warning: Implementation '{impl_name}' for service '{service_name}' not found. Skipping.")
            continue

        selected_implementations[service_name] = implementation

    return selected_implementations


def _select_manually(services: Dict[str, ServiceConfig]) -> Dict[str, ImplementationConfig]:
    """
    Prompts the user to manually select an implementation for each service.
    """
    # Load previous selections to set as defaults
    previous_selection = load_yaml_file(USER_SELECTION_FILE) or {}

    questions = [
        inquirer.List(
            service.name,
            message=f"Select implementation for '{service.name}' ({service.description})",
            choices=[None] + list(service.implementations.keys()),
            default=previous_selection.get(service.name)
        )
        for service in services.values()
    ]

    answers = inquirer.prompt(questions)

    # Filter out any null answers and save the valid ones for next time
    valid_selections = {k: v for k, v in answers.items() if v is not None}
    save_yaml_file(USER_SELECTION_FILE, valid_selections)

    # Resolve the selected implementation names to their config objects
    return {
        service_name: services[service_name].implementations[impl_name]
        for service_name, impl_name in valid_selections.items()
    }


# --- Docker Compose Generation ---

def generate_docker_compose(selected_implementations: Dict[str, ImplementationConfig]):
    """
    Generates and saves a docker-compose.yml file from a Jinja2 template.

    Args:
        selected_implementations: A dict of the chosen service implementations.
    """
    print("Generating Docker Compose file from template...")

    # Prepare data for the template
    # Collect all unique volume names needed by the selected services
    all_volumes = set()
    for impl in selected_implementations.values():
        if impl.volumes:
            for vol in impl.volumes:
                all_volumes.add(vol)

    # Create a Jinja2 template object
    template_contents = load_text_file(DOCKER_COMPOSE_TEMPLATE)
    template = Template(template_contents)

    # Render the template with the prepared data
    rendered_compose = template.render(
        implementations=selected_implementations,
        all_volumes=sorted(list(all_volumes))  # sort for consistent output
    )

    save_text_file(DOCKER_COMPOSE_FILE, rendered_compose)
    print(f"'{DOCKER_COMPOSE_FILE}' has been generated successfully.")


def generate_docker_compose_(selected_implementations: Dict[str, ImplementationConfig]):
    """
    Generates and saves a docker-compose.yml file from the selected implementations.

    Args:
        selected_implementations: A dict of the chosen service implementations.
    """
    print("Generating Docker Compose file...")
    compose_dict = _build_compose_dict(selected_implementations)
    save_yaml_file(DOCKER_COMPOSE_FILE, compose_dict)
    print(f"'{DOCKER_COMPOSE_FILE}' has been generated successfully.")


def _build_compose_dict(selected_implementations: Dict[str, ImplementationConfig]) -> dict:
    """
    Constructs the Docker Compose configuration as a Python dictionary.

    This is a more robust method than string formatting.
    """
    # Base structure with a default RabbitMQ service
    compose_services = {
        "rabbitmq": {
            "image": "rabbitmq:4-management-alpine",
            "container_name": "${COMPOSE_PROJECT_NAME}_Backbone",
            "hostname": "rabbitmq",
            "ports": ["5672:5672", "15672:15672"],
            "environment": {
                "RMQ_DEFAULT_USER": "guest",
                "RMQ_DEFAULT_PASS": "guest",
            },
            "volumes": ["rabbitmq_data:/var/lib/rabbitmq"],
        }
    }
    compose_volumes = {"rabbitmq_data": None}

    # Add selected services to the dictionary
    for service_name, impl in selected_implementations.items():
        service_entry = {
            "image": impl.image,
            "container_name": impl.container_name or f"${{COMPOSE_PROJECT_NAME}}_{impl.service}",
            "depends_on": ["rabbitmq"] + impl.depends_on,
            "env_file": [".env"]
        }
        if impl.environment:
            service_entry["environment"] = impl.environment
        if impl.ports:
            service_entry["ports"] = [f"{p}" for p in impl.ports]
        if impl.volumes:
            service_entry["volumes"] = [f"{v}:{v}" for v in impl.volumes]
            for v in impl.volumes:
                compose_volumes[v] = None  # Add named volume to the top-level volumes key

        compose_services[impl.docker_service_name] = service_entry

    return {
        "name": "Potato",
        "services": compose_services,
        "volumes": compose_volumes,
    }


# --- Docker Operations and Health Checks ---

def run_docker_compose_up() -> bool:
    """Runs 'docker compose up' to start the services."""
    print("Starting services with Docker Compose...")
    command = [
        "docker", "compose",
        "-f", str(DOCKER_COMPOSE_FILE),
        "up", "--build", "-d"
    ]
    try:
        print("-" * 30)
        subprocess.run(command, check=True)
        print("-" * 30)
        print("Docker containers are starting in the background...")
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 30)
        print(f"Error running Docker Compose: {e}")
        print("Please check if Docker is running and the configuration is valid.")
    except FileNotFoundError:
        print("-" * 30)
        print("Error: 'docker' command not found. Is Docker installed and in your PATH?")
    return False


def perform_health_checks(selected_implementations: Dict[str, ImplementationConfig]):
    """
    Performs HTTP health checks for services that have them configured.
    """
    results = check_urls_in_parallel(selected_implementations)

    print("\n--- Health Checks Complete ---")
    if all(results.values()):
        print("✔️ All services are healthy!")
    else:
        print("⚠️ Some services are not healthy:")
        for service_name, is_healthy in results.items():
            if not is_healthy:
                print(f"  - {service_name}")


# --- Main Execution ---

def main():
    """The main entry point for the script."""
    print("--- Welcome to the Potato Launcher 🚀 ---")

    # 1. Load service definitions
    services = load_services_config(CONFIG_FILE)

    # 2. Let the user select implementations
    selected_implementations = select_implementations(services)

    if not selected_implementations:
        print("No implementations selected. Exiting.")
        return

    print("--- Selected Implementations ---")
    for service, impl in selected_implementations.items():
        print(f"- {service}: {impl.name} ({impl.description})")

    # 3. Generate the docker-compose.yml file
    generate_docker_compose(selected_implementations)

    # 4. Start the services
    up = run_docker_compose_up()

    if up:
        # 5. Perform health checks
        perform_health_checks(selected_implementations)

        print("\n--- Launch process complete! ---")


if __name__ == '__main__':
    main()

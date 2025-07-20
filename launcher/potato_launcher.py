import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import inquirer
import requests
import yaml


@dataclass
class HealthCheckConfig:
    port: int
    path: str
    interval: int = 5  # seconds
    attempts: int = 5


@dataclass
class ImplementationConfig:
    name: str
    service: str
    docker_service_name: str
    description: str
    image: str
    container_name: Optional[str] = None
    environment: Optional[dict] = None
    volumes: Optional[list] = None
    ports: Optional[list[str]] = None
    health_check: Optional[HealthCheckConfig] = None
    depends_on: Optional[list] = None

    def __post_init__(self):
        if self.health_check is not None:
            if not self.ports:
                raise ValueError("health_check requires ports!")
            for port in self.ports:
                if self.health_check.port == int(port.split(":")[0]):
                    break
            else:
                print(self.ports, self.health_check.port)
                raise ValueError("health_check port not found in ports!")


@dataclass
class ServiceConfig:
    name: str
    description: str
    implementations: dict[str, ImplementationConfig]


def load_config(file_path: Path) -> dict[str, ServiceConfig]:
    with open(file_path) as f:
        config_data = yaml.safe_load(f)

    services = {}
    for service_type, service_data in config_data.items():
        implementations = service_data["implementations"]
        service_name = service_data.get("name", service_type)
        for i, implementation in enumerate(implementations):
            if implementation.get("health_check"):
                implementations[i]["health_check"] = HealthCheckConfig(**implementations[i]["health_check"])
            implementations[i] = ImplementationConfig(**implementation, service=service_name)

        services[service_name] = (ServiceConfig(
            name=service_name,
            description=config_data[service_type]["description"],
            implementations={imp.name: imp for imp in implementations},
        ))

    return services


def load_presets(dir_path: Path) -> list[Path]:
    return list(dir_path.glob("*.yaml"))


def load_user_selection(file_path: Path) -> dict:
    with open(file_path) as f:
        config_data = yaml.safe_load(f)

    return config_data


def save_user_selection(file_path: Path, selection: dict):
    with open(file_path, "w") as f:
        yaml.dump(selection, f)


def chose_implementations():
    services = load_config(Path("services_config.yaml"))

    presets = load_presets(Path("Presets"))

    if presets:
        selection = inquirer.prompt([
            inquirer.List(
                "preset",
                message="Select a preset",
                choices=[None] + [i.stem for i in presets],
            )
        ])

        if selection["preset"]:
            print(f"Loading preset: {selection['preset']}")
            with open(f"Presets/{selection["preset"]}.yaml") as f:
                preset_data = yaml.safe_load(f)

            selected_implementations = {}

            for service_type, implementation_name in preset_data.items():
                selected_implementations[service_type] = services[service_type].implementations.get(implementation_name)

            if not all(selected_implementations.values()):
                for service_type, implementation in selected_implementations.items():
                    if not implementation:
                        print(f"Missing implementation for {service_type}")
            return selected_implementations

    user_selection_path = Path("user_selection.yaml")
    if user_selection_path.exists():
        user_selection = load_user_selection(user_selection_path)
    else:
        user_selection = {}

    selection = inquirer.prompt([
        inquirer.List(
            service_name,
            message=f"Select a {service_name}",
            choices=[imp_name for imp_name in service.implementations.keys()] + [None],
            default=user_selection.get(service_name, None)
        )
        for service_name, service in services.items()
    ])

    save_user_selection(Path("user_selection.yaml"), selection)

    selected_implementations = {
        service_name: imp
        for service_name, service in services.items()
        if selection[service_name]
        for imp_name, imp in
        service.implementations.items()
        if selection[service_name] == imp_name
    }

    return selected_implementations


def generate_docker_compose(selected_implementations):
    service_template = """
  {docker_service_name}:
    # build:
    #   context: ./services
    #   dockerfile: ear/heartbeat/Dockerfile
    image: {image}
    container_name: {container_name}
    env_file:
      - .env{extra}
    depends_on:
      - rabbitmq
      {depends_on}
    """

    compose = """
name: {name}

services:
  rabbitmq:
    image: rabbitmq:4-management-alpine
    container_name: ${{COMPOSE_PROJECT_NAME}}_Backbone
    hostname: rabbitmq  # Important for services to find it
    ports:
      - "5672:5672"  # Standard AMQP port
      - "15672:15672"  # Management port  (http://localhost:15672)
    environment:
      RMQ_DEFAULT_USER: "guest"
      RMQ_DEFAULT_PASS: "guest" # CHANGE THIS FOR PRODUCTION! (but fine for dev)
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq # Persist data (queues, messages)

{services}
volumes:
  rabbitmq_data:
{volumes}"""

    services = ""

    for service_name, imp in selected_implementations.items():
        extra = ""

        if imp.environment:
            extra += "\n    environment:"
            for k, v in imp.environment.items():
                extra += f"\n      - {k}={v}"

        if imp.volumes:
            extra += "\n    volumes:"
            for v in imp.volumes:
                extra += f"\n      - {v}:{v}"

        if imp.ports:
            extra += "\n    ports:"
            for v in imp.ports:
                extra += f"\n      - {v}"

        services += service_template.format(
            docker_service_name=imp.docker_service_name,
            image=imp.image,
            container_name=f"{imp.container_name or f"${{COMPOSE_PROJECT_NAME}}_{service_name}"}",
            extra=extra,
            depends_on="\n      - ".join(f"{v}" for v in imp.depends_on) if imp.depends_on else ""
        )

    volumes = ""
    for service_name, imp in selected_implementations.items():
        if imp.volumes:
            for v in imp.volumes:
                volumes += f"  {v}:\n"

    compose = compose.format(name="Potato", services=services, volumes=volumes)

    with open("docker-compose.yml", "w") as f:
        f.write(compose)


def health_checks(selected_implementations):
    for service_name, imp in selected_implementations.items():
        if not imp.health_check:
            print(f"No ports defined for {imp.docker_service_name}")
            continue
        check_config = imp.health_check
        print(
            f"Checking health of {imp.docker_service_name} on port {check_config.port} every {check_config.interval} seconds")
        print(type(imp.health_check.interval))

        url = f"http://localhost:{check_config.port}{check_config.path}"
        for _ in range(check_config.attempts):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    print(f"{imp.docker_service_name} is healthy!")
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(check_config.interval)
        else:
            print(f"Error: {imp.docker_service_name} failed health check.")


def main():
    imps = chose_implementations()

    print(imps)

    if not imps:
        print("No implementations selected.")
        return

    generate_docker_compose(imps)

    import subprocess
    subprocess.run(["docker", "compose", "-f", "docker-compose.yml", "up", "--build", "-d"])

    # TODO: check for running/ existing containers
    #       check for missing images
    #       networks?

    health_checks(imps)


if __name__ == '__main__':
    main()

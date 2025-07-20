import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def check_urls_in_parallel(services: dict, max_workers=10):
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(check_url_health,
                                         service
                                         ): service for service in services.values()}
        for future in as_completed(future_to_url):
            service, is_healthy = future.result()
            results[service] = is_healthy
    return results


def check_url_health(service):
    # print(f"Checking '{impl.docker_service_name}' at {url}")
    # print(f"Beginning check in {check_config.interval} seconds...")

    health_check = service.health_check
    url = f"http://localhost:{health_check.port}{health_check.path}"

    attempts = 5
    interval = 5

    for attempt in range(attempts):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                # print(f"  -> Success: '{impl.docker_service_name}' is healthy!")
                return service.name, True
            else:
                print(f"  -> Attempt {attempt + 1}/{attempts}: Received status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  -> Attempt {attempt + 1}/{attempts}: Connection failed. Retrying...")
        time.sleep(interval)

    # print(f"  -> Error: '{impl.docker_service_name}' failed all health checks.")
    return service.name, False


def main():
    pass


if __name__ == '__main__':
    main()

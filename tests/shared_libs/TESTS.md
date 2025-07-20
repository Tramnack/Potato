# HealthCheckMixin

## Tests:

### test_initialization_with_valid_port

Tests that the mixin initializes correctly with a valid port.

### test_initialization_with_invalid_port

Tests that the mixin raises an error when initialized with an invalid port.

### test_no_app_initialization

Tests the `no_app` class method of the mixin.

### test_ready_property

Tests the `ready` property of the mixin.

### test_no_app_initialization_ready_property

Tests the `ready` property of the mixin when `no_app` is True.

### test_status_property

Tests the `status` property of the mixin.

### test_uptime_property

Tests the `uptime` property of the mixin.

### test_health_endpoint_ready

Tests the `/health` endpoint when the service is ready.

### test_health_endpoint_not_ready

Tests the `/health` endpoint when the service is not ready.

### test_status_endpoint_ready

Tests the `/status` endpoint when the service is ready.

### test_status_endpoint_not_ready

Tests the `/status` endpoint when the service is not ready.

### test_health_server_starts_in_thread

Tests that the health server is started in a separate thread.
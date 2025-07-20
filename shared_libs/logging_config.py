import logging.config
import os


def setup_logging(service_name="potato_service", log_level=None):
    """
    Sets up consistent logging for a given service or component.

    :param service_name: The name of the service/component (e.g., 'ear-mic', 'brain-llm').
                         Used in log messages to identify the source.
    :param log_level: The desired log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                      Defaults to INFO if not specified, or reads from LOG_LEVEL env var.
    """
    default_log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level = getattr(logging, default_log_level, logging.INFO)

    # Basic configuration dictionary (can be expanded significantly)
    # Using dictionary config is generally recommended over basicConfig
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,  # Don't disable existing loggers (e.g., from imported libraries)

        'formatters': {
            'standard': {
                # Add service_name to the format
                'format': f'[%(asctime)s] [%(levelname)s] [{service_name}] (%(name)s): %(message)s'
            },
            'json': {
                # For structured logging, useful if you ever move to ELK/Grafana Loki stack
                'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "service": "' + service_name + '", "logger": "%(name)s", "message": "%(message)s"}'
            }
        },
        'handlers': {
            'console': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',  # Send logs to stdout
            },
            # You could add a file handler here for local file logging if desired:
            # 'file_handler': {
            #     'level': level,
            #     'formatter': 'standard',
            #     'class': 'logging.handlers.RotatingFileHandler',
            #     'filename': f'/var/log/{service_name}.log', # Path inside container
            #     'maxBytes': 10485760, # 10MB
            #     'backupCount': 5,
            # }
        },
        'loggers': {
            # Root logger configuration
            '': {
                'handlers': ['console'],  # Add 'file_handler' if you use it
                'level': level,
                'propagate': False  # Prevent logs from being sent to root handler twice
            },
            # Specific logger for pika (RabbitMQ client) to control its verbosity
            'pika': {
                'handlers': ['console'],
                'level': 'WARNING',  # Keep pika logs less verbose by default
                'propagate': False
            },
            # You can add more specific loggers here for different modules if needed
        }
    }

    logging.config.dictConfig(LOGGING_CONFIG)

    # Return the logger for the specific service, so modules can get it
    return logging.getLogger(service_name)

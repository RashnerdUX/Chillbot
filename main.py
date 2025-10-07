from logging import config, getLogger, Logger
import os
import json

# Load the logging configuration
logging_config_path = "logging_config.json"
if os.path.exists(logging_config_path):
    # If the logging_config.json exists then load it and config the logger
    with open(logging_config_path) as cfg:
        config_file = json.load(cfg)

    # Set the configuration
    config.dictConfig(config_file)

    # Load the logger
    appLogger = getLogger(__name__)
    appLogger.info("Application logger configuration complete. Loggers synchronized.")


# Load up the variables that need to be set with FastAPI
class Appstate:
    def __init__(self):
        self.app_logger: Logger = None
    pass

# Store in the App state variable in this and pass to FastAPI App instance for application
app_state = Appstate()
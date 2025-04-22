import logging

def configure_logging(log_file=None):
    """
    Configure logging for the project.
    """
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file) if log_file else logging.StreamHandler()
        ]
    )
    logging.info("Logging configured successfully.")
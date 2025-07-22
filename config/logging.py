import logging

class ModuleFilter(logging.Filter):
    def filter(self, record):
        record.module_name = record.name.split('.')[-1]
        return True

def setup_logging():
    """Setting up the formation and registration of levels for the entire project."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(module)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger().addFilter(ModuleFilter())
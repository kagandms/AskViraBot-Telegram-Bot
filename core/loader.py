import importlib
import inspect
import logging
import pkgutil

from telegram.ext import Application

logger = logging.getLogger(__name__)


def load_handlers(app: Application):
    """
    Automatically discovers and loads handler modules from the 'handlers' package.
    Each module MUST have a 'setup(app)' function to be loaded.
    """
    import handlers

    # Iterate through all modules in the 'handlers' package
    package_path = handlers.__path__
    prefix = handlers.__name__ + "."

    for _, name, _is_pkg in pkgutil.iter_modules(package_path, prefix):
        # Allow loading packages (like 'handlers.games') if they have setup()
        # if is_pkg: continue

        try:
            module = importlib.import_module(name)

            # Check if module has a 'setup' function
            if hasattr(module, "setup") and inspect.isfunction(module.setup):
                logger.info(f"🔌 Loading module: {name}")
                module.setup(app)
            else:
                logger.debug(f"⚠️ Skipped module {name}: No 'setup(app)' function found.")

        except Exception as e:
            logger.error(f"❌ Failed to load module {name}: {e}", exc_info=True)

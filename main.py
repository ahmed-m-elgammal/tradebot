"""
Trading Bot Main Entry Point

Initialize all systems and start the trading bot.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import load_config
from src.utils.logger import setup_logging, get_logger


def initialize_systems(env='dev'):
    """
    Initialize all bot systems.
    
    Args:
        env: Environment ('dev' or 'prod')
        
    Returns:
        Loaded configuration
    """
    # Load configuration
    config = load_config(env)
    
    # Set up logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        format_type=config.logging.format,
        console=config.logging.console
    )
    
    logger = get_logger(__name__)
    logger.info(f"Trading bot initialized in {env} environment")
    logger.info(f"Configuration loaded successfully")
    
    return config


def main():
    """Main entry point."""
    logger = get_logger(__name__)
    
    try:
        # Initialize
        config = initialize_systems()
        
        logger.info("="*60)
        logger.info("TRADING BOT STARTED")
        logger.info("="*60)
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Log level: {config.logging.level}")
        logger.info(f"Risk limits: max_position={config.risk.limits.max_position_size:.1%}, "
                   f"max_heat={config.risk.limits.max_portfolio_heat:.1%}")
        
        # TODO: Start trading logic here
        logger.info("Trading bot ready!")
        
    except Exception as e:
        logger.error(f"Fatal error starting trading bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

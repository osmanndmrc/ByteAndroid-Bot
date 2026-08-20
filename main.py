"""
Main entry point for SnapBot Android automation daemon.
"""

import sys
import argparse
from loguru import logger
from core.bot import SnapBot


def parse_args():
    parser = argparse.ArgumentParser(description="SnapBot - Production Snapchat Automation Bot for ReDroid")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Trigger an immediate snap workflow run instead of waiting for scheduler",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        bot = SnapBot(config_path=args.config)
        
        if args.now:
            logger.info("Executing immediate Snap workflow requested via --now CLI flag...")
            success = bot.trigger_immediate_run()
            sys.exit(0 if success else 1)
        else:
            bot.run_forever()
    except Exception as e:
        logger.critical(f"Fatal error in main entrypoint: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

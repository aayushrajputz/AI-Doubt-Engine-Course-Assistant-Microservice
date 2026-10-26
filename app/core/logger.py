import sys
from loguru import logger

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level> {level:<8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message} </level>",
    level="DEBUG"
)


logger.add(
    "logs/app.log",
    rotation="50 MB",       # 50MB hote hi naya file banaye
    retention="10 days",    # 10 din purane logs delete kar de
    compression="zip",      # Purane logs zip compress kare
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
) 
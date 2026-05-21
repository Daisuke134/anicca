import logging
import os
from logging import FileHandler, Formatter, StreamHandler, getLogger


def get_log_level():
    # 環境変数からログレベルを取得（デフォルトは'INFO'）
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

    # ログレベルの対応表
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    return level_map.get(log_level_str, logging.INFO)


# ロガーの取得
logger = getLogger(__name__)

# 環境変数から取得したログレベルを設定
logger.setLevel(get_log_level())

# ログのフォーマット設定
formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# コンソールハンドラの設定
console_handler = StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ファイルハンドラの設定
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
file_handler = FileHandler(os.path.join(log_dir, "application.log"))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

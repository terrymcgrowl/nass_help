import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    support_group_id: int
    data_dir: str
    db_name: str
    max_db_connections: int
    db_timeout: float


class ConfigError(Exception):
    pass


def _load_env() -> None:
    load_dotenv()


def _get_required_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ConfigError(f"{key} не найден в переменных окружения")
    return value


def _get_optional_env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _parse_int(value: str, key: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{key} должен быть числом, получено: {value}")


def _parse_float(value: str, key: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ConfigError(f"{key} должен быть числом, получено: {value}")


_config_instance: Config | None = None


def get_config() -> Config:
    global _config_instance
    
    if _config_instance is not None:
        return _config_instance
    
    _load_env()
    
    bot_token = _get_required_env('BOT_TOKEN')
    support_group_id_str = _get_required_env('SUPPORT_GROUP_ID')
    support_group_id = _parse_int(support_group_id_str, 'SUPPORT_GROUP_ID')
    
    data_dir = _get_optional_env('DATA_DIR', 'data')
    db_name = _get_optional_env('DB_NAME', 'database.db')
    
    max_connections_str = _get_optional_env('MAX_DB_CONNECTIONS', '5')
    max_db_connections = _parse_int(max_connections_str, 'MAX_DB_CONNECTIONS')
    
    db_timeout_str = _get_optional_env('DB_TIMEOUT', '10.0')
    db_timeout = _parse_float(db_timeout_str, 'DB_TIMEOUT')
    
    _config_instance = Config(
        bot_token=bot_token,
        support_group_id=support_group_id,
        data_dir=data_dir,
        db_name=db_name,
        max_db_connections=max_db_connections,
        db_timeout=db_timeout
    )
    
    return _config_instance

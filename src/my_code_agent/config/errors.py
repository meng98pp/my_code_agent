"""配置与启动错误。不在 import 时抛出。"""


class ConfigError(Exception):
    """用户可修复的配置问题。"""


class MissingAPIKeyError(ConfigError):
    """未设置 API_KEY。"""


class DataRootOnCDriveError(ConfigError):
    """数据根或记忆根落在 C 盘。"""

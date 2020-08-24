import configparser

from os.path import expanduser

from . import CONFIG_FILE

config_path = expanduser(CONFIG_FILE)
_config = None
dirty = False


def load():
    global _config
    global dirty

    _config = configparser.ConfigParser()
    _config.read(config_path)

    if 'telegram' not in _config.sections():
        _config['telegram'] = {}
        _config['telegram']['enable'] = str(False)

    if 'log' not in _config.sections():
        _config['log'] = {}
        _config['log']['filename'] = 'tq.log'

    dirty = False


def set(section, option, value):
    global dirty

    if section not in _config.sections():
        _config[section] = {}

    if option not in _config[section]:
        _config[section][option] = str(value)
        dirty = True

    if _config[section][option] != str(value):
        _config[section][option] = str(value)
        dirty = True


def get(section, option):
    if section not in _config.sections():
        return None

    if option not in _config[section]:
        return None

    return _config[section][option]


def save():
    if not dirty:
        return

    with open(config_path, 'w') as f:
        _config.write(f)

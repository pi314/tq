import configparser

from os.path import expanduser

from . import CONFIG_FILE

config_path = expanduser(CONFIG_FILE)
config = None
dirty = False


def load():
    global config
    global dirty

    config = configparser.ConfigParser()
    config.read(config_path)

    if 'telegram' not in config.sections():
        config['telegram'] = {}
        config['telegram']['enable'] = str(False)

    if 'log' not in config.sections():
        config['log'] = {}
        config['log']['filename'] = 'tq.log'

    dirty = False


def set(section, option, value):
    global dirty

    if section not in config.sections():
        config[section] = {}

    if option not in config[section]:
        config[section][option] = str(value)
        dirty = True

    if config[section][option] != str(value):
        config[section][option] = str(value)
        dirty = True


def get(section, option):
    if section not in config.sections():
        return None

    if option not in config[section]:
        return None

    return config[section][option]


def save():
    if not dirty:
        return

    with open(config_path, 'w') as f:
        config.write(f)

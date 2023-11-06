import configparser


def load_config(filename, autosave=True):
    config = configparser.ConfigParser()

    # Read config file
    try:
        with open(filename, "r") as config_file:
            config.read_file(config_file)
    except FileNotFoundError:
        print(f"Config file '{filename}' not found, using defaults")
    except configparser.Error as e:
        print(f"Error reading config file '{filename}': {e}, using defaults")

    default_values = {
        "library": {
            "db_url": "sqlite+aiosqlite:///:memory:",
            "media_path": "./media",
        },
        "storage": {
            "path": "./storage",
            "thumb_suffix": "-thumb.jpg",
        }
    }

    # Set default values if needed
    for section, options in default_values.items():
        if not config.has_section(section):
            config.add_section(section)
        for option, value in options.items():
            if not config.has_option(section, option):
                config.set(section, option, value)

    # Updates config with new defaults
    if autosave:
        save_config(config, filename)

    return config

def save_config(config, filename):
    # Write updated config file
    with open(filename, "w") as config_file:
        config.write(config_file)

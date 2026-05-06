from netbox.plugins import PluginConfig

from .version import __version__


class NetBoxCFBackrefsConfig(PluginConfig):
    name = "netbox_cf_backrefs"
    verbose_name = "NetBox Custom Field Backrefs"
    description = "Show reverse references from object / multi-object custom fields on the target object's detail page."
    version = __version__
    author = "Jan Krupa"
    author_email = "jan.krupa@cesnet.cz"
    base_url = "cf-backrefs"
    min_version = "4.5.0"
    max_version = "4.6.99"
    default_settings = {
        "page_size": 50,
        "excluded_custom_fields": [],
    }


config = NetBoxCFBackrefsConfig

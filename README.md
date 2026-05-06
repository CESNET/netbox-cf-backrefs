# netbox_cf_backrefs

NetBox plugin that surfaces the **reverse** side of object / multi-object custom field references on the target object's detail page.

If you create a custom field of type `object` (or `multi-object`) on a Device pointing to a Contact, NetBox shows the contact under the device — but the contact page has no indication of being referenced. This plugin adds an inline panel **"Referenced by Custom Fields"** to the contact page (and to every other NetBox object that is a current CF target).

## Compatibility

- NetBox 4.5.0 – 4.6.99
- Python 3.12 / 3.13 / 3.14

## Install

```bash
source /opt/netbox/venv/bin/activate
pip install netbox-cf-backrefs
```

Add to `configuration.py`:

```python
PLUGINS = ["netbox_cf_backrefs"]

PLUGINS_CONFIG = {
    "netbox_cf_backrefs": {
        "page_size": 50,
        "excluded_custom_fields": [],
    }
}
```

Restart NetBox.

## Settings

| Key | Default | Description |
|---|---|---|
| `page_size` | `50` | Rows per page in the panel paginator. |
| `excluded_custom_fields` | `[]` | List of CF *names* (not labels) to suppress from all backref panels. |

## Behavior notes

- **No permission filtering.** Every viewer sees the same complete list of references. If user X has no `view` permission on Device-1 but Device-1 references the Contact they are viewing, Device-1 will still appear (as a clickable link). Choose this plugin only if that trade-off is acceptable for your deployment.
- **CFs marked `ui_visible='hidden'` are skipped** — admin-only CFs won't leak through the panel.
- **Restart required when adding/removing object-CFs** — the plugin discovers CF target models at NetBox startup. Adding a new CF later requires a NetBox restart for it to take effect on the panel.
- **Empty panels are hidden.** If no objects currently reference the target via CFs, the panel is not rendered.

## Development

```bash
make test       # /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb
make lint       # ruff + djlint --check
make format     # ruff format + djlint --reformat
```

## License

Apache-2.0

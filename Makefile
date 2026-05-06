PY = /opt/netbox/venv/bin/python
MANAGE = $(PY) /opt/netbox/netbox/manage.py

.PHONY: test lint format

test:
	$(MANAGE) test netbox_cf_backrefs --keepdb

lint:
	$(PY) -m ruff check netbox_cf_backrefs
	$(PY) -m djlint netbox_cf_backrefs/templates --check

format:
	$(PY) -m ruff format netbox_cf_backrefs
	$(PY) -m djlint netbox_cf_backrefs/templates --reformat

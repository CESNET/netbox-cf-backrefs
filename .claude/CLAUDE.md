# CLAUDE.md

**NetBox Compatibility:** 4.5.0 - 4.6.99
**Python:** >=3.12,<3.15 (3.12/3.13/3.14)

- use ruff from python formating
- use djlint for templates formatting
- These commands assume a local NetBox environment at `/opt/netbox`:
    - source /opt/netbox/venv/bin/activate
    - /opt/netbox/venv/bin/python3 /opt/netbox/netbox/manage.py nbshell
    -  /opt/netbox/venv/bin/python3 /opt/netbox/netbox/manage.py runserver 

## Plan Mode
- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of each plan, give me a list of unresolved questions to answer, if any.
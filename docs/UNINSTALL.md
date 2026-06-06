# Uninstall

If installed in a virtual environment:

```bash
deactivate
rm -rf .venv
```

If installed globally:

```bash
python3 -m pip uninstall nexpilot-public
```

Stop any running `nexpilot` process. No LaunchAgent, service, database, or
background daemon is installed by this public trial package.

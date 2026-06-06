# Release Checklist

Before pushing or publishing:

- [ ] Confirm this is the clean `nexpilot-public` tree, not M4ControlCenter.
- [ ] Run `python3 -m compileall src tests`.
- [ ] Run `python3 scripts/secret-scan.py .`.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest`.
- [ ] Run a local agent and `python3 scripts/smoke-terminal.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'`.
- [ ] Confirm `git status -sb` only includes intentional release files.
- [ ] Confirm `.env`, databases, logs, backups, private keys, and runtime state
  are not tracked.
- [ ] Confirm README says public internet exposure is unsupported.
- [ ] Confirm GitHub visibility with Rain before pushing.
- [ ] Push private beta with `bash scripts/publish-github.sh`.
- [ ] Verify GitHub Actions CI passes on `main`.

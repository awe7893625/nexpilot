# Release Checklist

Before pushing or publishing:

- [ ] Confirm this is the clean `nexpilot-public` tree, not M4ControlCenter.
- [ ] Run `python3 -m compileall src tests`.
- [ ] Run `python3 scripts/secret-scan.py .`.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python3 -m pytest`.
- [ ] Run `bash scripts/review-gate.sh`.
- [ ] Run a local agent and `python3 scripts/smoke-terminal.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'`.
- [ ] Run `python3 scripts/smoke-reconnect.py --url 'ws://127.0.0.1:8765/ws/terminal?token=test-token'`.
- [ ] Confirm `git status -sb` only includes intentional release files.
- [ ] Confirm `.env`, databases, logs, backups, private keys, and runtime state
  are not tracked.
- [ ] Confirm README says public internet exposure is unsupported.
- [ ] Confirm README and SECURITY say tester access is non-transferable.
- [ ] Confirm Terminal Grade Beta limitations are documented.
- [ ] Build per-tester tarballs with `bash scripts/make-tester-package.sh TESTER_ID`.
- [ ] Confirm GitHub visibility with Rain before pushing.
- [ ] Push private beta with `bash scripts/publish-github.sh`.
- [ ] Verify GitHub Actions CI passes on `main`.

# Sample project — deliberately sloppy

Scan it:

```bash
python3 ../slop-scan.py sample-project
```

Expected findings (verify against your run):

- `HIGH duplicate_block` — `load_config_backup` and `save_config` each repeat
  the same 6-line `with open(...)` window 6 times (threshold is 3)
- `HIGH debug_leftover` — `breakpoint()` left in `save_config`
- `HIGH unimplemented_stub` — `raise NotImplementedError` in `delete_config`
- `MED todo_density` — 4 TODOs in `load_config`
- `MED placeholder` — the `...` in `delete_config`

Exit code will be `1` because HIGH findings are present. That's the point:
this fixture is the "does the scanner actually fire" smoke test.

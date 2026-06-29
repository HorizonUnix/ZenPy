# Changelog

## [0.2.0] - 2026-06-30

### Added
- Public library API: `from zenmaster import detect, apply, runner, smu, CpuInfo`
- `runner.is_flag_arg()` to query args that take no value
- `vrmcvip-current` (VanGogh) for full RyzenAdj arg parity

### Changed
- Linux PCI backend now probes writability with a `0x47` register round-trip
  (like UXTU4Linux) instead of only checking that the config file exists, so a
  non-writable bus (no root, lockdown) fails at init with a clear message
- Unified project description to "Adjust power management settings for Ryzen
  CPUs on Linux and Windows"
- Rewrote README with a fuller overview, compatibility table, and an accurate
  RyzenAdj comparison
- Args that require a value now report an error (or show help on the CLI)
  when passed without `=value`, instead of silently sending 0
- `apply()` results always include a consistent set of keys (`error` is
  `None` on success), making the return shape stable for consumers
- Argument names are normalised to lowercase/hyphen form in `apply()` results
- Modernised packaging to PEP 639 SPDX license metadata

### Fixed
- `--skin-temp-limit` (a power limit in mW) is no longer multiplied by 256;
  only the temperature args `apu-skin-temp` and `dgpu-skin-temp` are scaled,
  matching RyzenAdj
- Negative values (e.g. Curve Optimiser `--set-coall=-20`) now wrap to
  unsigned 32-bit like RyzenAdj, instead of being clamped to 0
- Flag args (`--max-performance`, `--enable-oc`, …) always send 0, ignoring any
  value passed, matching RyzenAdj's boolean handling
- `smu.send_*` now raise a clear error if called before `smu.init()`
- `smu.init()` is idempotent and no longer leaks the Windows PawnIO handle
- CLI shows help for a malformed argument before requiring root
- `apply()` handles malformed preset strings (unclosed quotes) gracefully
- `--table` no longer shows duplicate TDC values in EDC rows on Zen 5 tables

## [0.1.1] - 2026-06-30

### Fixed
- Workflow and packaging fixes for initial PyPI release

## [0.1.0] - 2026-06-29

### Added
- Initial release
- Cross-platform AMD Ryzen SMU power management for Linux and Windows
- Dynamic `--help` showing only args supported by the detected CPU
- `--table` for labeled live PM table (temps, power, currents)
- `--json` for machine-readable output
- `--reapply=N` to continuously re-apply a preset
- `--info` to show CPU family, socket, and active backend
- Linux backends: `ryzen_smu` kernel module and PCI direct access
- Windows backend: PawnIO (replaces WinRing0 used by RyzenAdj)
- Embeddable Python library — `import zenmaster`
- Zero mandatory dependencies

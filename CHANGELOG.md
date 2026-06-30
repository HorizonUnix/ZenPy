# Changelog

## [0.4.0] - 2026-06-30

### Added
- CLI `--sensors` (and `--sensors --json`): compact live readout of temp, load, socket power, iGPU clock/temp, and memory clock
- CLI `--info` now shows a `Driver` line with the driver name, version, and status (or `PCI direct access`); same data under `--info --json`
- `smu.read_pm_sensors(family)` reads and decodes the PM table in one call, returning a `PmSensors` (or `None`). `table.read_sensors(data, ver)` decodes raw bytes you already have
- `smu.module_status()` returns one `ModuleStatus` verdict for the driver (`ok`, `version`, `min_version`, `reason`). Helpers: `module_version()`, `module_version_ok()`, `is_available()`, `secure_boot_enabled()`, `driver_name()`
- `smu.ensure_backend()`: like `init()` but returns the backend or `None` instead of raising
- `smu.unavailable_reason()`: the message explaining why the SMU can't be used, or `None` when it can
- `smu.send_arg(family, name, value)` sends one value to every mailbox the arg maps to, returning `[(mailbox, opcode, status), ...]`
- `resolve(name, cpu_family, cpu_model)` builds a `CpuInfo` from explicit values without reading `/proc/cpuinfo`
- `runner.is_supported(family)`
- All of the above are re-exported at the top level, so apps don't import from `zenmaster.linux`

### Changed
- Linux now checks the `ryzen_smu` version (`drv_version`) and requires `>= 0.1.7`, with the installed version in the error
- Backend selection follows Secure Boot: off uses PCI direct access, on uses `ryzen_smu`. A loaded module is no longer preferred over PCI when Secure Boot is off
- On Windows, the driver is PawnIO with no version requirement, and Secure Boot does not apply

## [0.3.0] - 2026-06-30

### Added
- `get-*` query commands now return the value the SMU reports, shown in the CLI and in `--json` as a `returned` field; `smu.query_mp1()` / `smu.query_rsmu()` expose the raw read-back for library users
- `--version` flag, which prints the installed version and checks PyPI for a newer release; `zenmaster.check_update()` exposes the same check to library users
- Exception hierarchy for library users: `ZenMasterError` (base) with `BackendUnavailable`, `SMUNotInitialized`, `UnsupportedCPU`, all still subclass `RuntimeError`, so existing `except RuntimeError` keeps working
- `smu.SmuStatus` IntEnum for SMU status codes (`SMU_OK` etc. now alias it)
- `ApplyResult` TypedDict documenting the `apply()` result contract
- `py.typed` marker so downstream type-checkers use the bundled type hints
- PM-table support for the Raven/Picasso-era APUs (RavenRidge, Picasso, Dali, Pollock), which use a distinct table opcode set
- Linux can now read the PM table over PCI direct access (via `/dev/mem`) when `ryzen_smu` is not loaded

### Changed
- `tdc-limit` and `edc-limit` now have descriptions and appear under "VRM & Currents" in `--help` instead of "Unknown command"
- Moved the MP1/RSMU mailbox tables, SMU status codes, and PM-table metadata into shared modules (`mailbox.py`, `pmtable.py`)
- Unified the Linux register send/poll path into one routine shared by the `ryzen_smu` and PCI backends; simplified `apply()` token parsing
- Removed unused `runner` helpers (`get_socket_short`, `has_smu_support`, `get_commands`)

### Fixed
- Windows `--table` / `--dump-table` now work on VanGogh (Steam Deck) and Mendocino, which were missing from the PM-table family list

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
- Argument names are normalized to lowercase/hyphen form in `apply()` results
- Modernized packaging to PEP 639 SPDX license metadata

### Fixed
- Windows PM table read now aborts if the final table-transfer retry is still
  rejected, instead of reading stale/garbage physical memory
- Windows SMU polling sleeps briefly after a fast initial spin, avoiding a busy
  loop that pinned a core while waiting for the mailbox
- `--skin-temp-limit` (a power limit in mW) is no longer multiplied by 256;
  only the temperature args `apu-skin-temp` and `dgpu-skin-temp` are scaled,
  matching RyzenAdj
- Negative values (e.g. Curve Optimizer `--set-coall=-20`) now wrap to
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
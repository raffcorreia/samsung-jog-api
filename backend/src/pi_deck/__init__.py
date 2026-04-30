"""`pi_deck` — Raspberry Pi control deck backend (CJ791 JOG project).

Subpackages: `api`, `services`, `hardware`, `storage`, `models`.
Bench bring-up scripts live under the repository `scripts/` directory.
See docs/architecture.md (Repository layout) and docs/development/code-guidelines.md.
"""

try:
    from pi_deck._version import __version__
except ImportError:
    __version__ = "0.0.0-dev"

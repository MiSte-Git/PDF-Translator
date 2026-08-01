"""Ad-hoc script exercising pipeline/translation/protected_terms.py.

Not a pytest test - run manually:

    python tests/manual_test_protected_terms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.translation.protected_terms import (
    derive_protected_term,
    protect_terms,
    restore_terms,
)


def main() -> None:
    term = derive_protected_term("1526 VIRELICON.pdf")
    print(f"derive_protected_term('1526 VIRELICON.pdf') -> {term!r}")
    assert term == "VIRELICON", f"expected 'VIRELICON', got {term!r}"

    no_prefix_term = derive_protected_term("Virelicon.pdf")
    print(f"derive_protected_term('Virelicon.pdf') -> {no_prefix_term!r}")
    assert no_prefix_term == "Virelicon", f"expected 'Virelicon', got {no_prefix_term!r}"

    html = (
        "<p>The <b>VIRELICON</b> Prism was born. Virelicon is not a tool. "
        "Some say virelicon bends truth.</p>"
    )
    print(f"\nOriginal html:\n  {html}")

    protected_html, mapping = protect_terms(html, [term])
    print(f"\nProtected html:\n  {protected_html}")
    print(f"Mapping: {mapping}")

    assert "VIRELICON" not in protected_html
    assert "Virelicon" not in protected_html
    assert "virelicon" not in protected_html
    assert len(mapping) == 3

    # Simulate translation leaving placeholders untouched.
    fake_translated_html = protected_html.replace("was born", "wurde geboren")
    restored_html = restore_terms(fake_translated_html, mapping)
    print(f"\nRestored html:\n  {restored_html}")

    assert "<b>VIRELICON</b>" in restored_html
    assert "Virelicon is not a tool" in restored_html
    assert "virelicon bends truth" in restored_html
    assert "wurde geboren" in restored_html

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()

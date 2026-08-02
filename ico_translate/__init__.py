"""Application layer specific to the one Google-Drive ICO folder (source
selection, review tooling, batch orchestration). Does not belong under
pipeline/ - pipeline/word, pipeline/pdf and pipeline/translation stay
generic (translate any Word/PDF document, no folder- or ICO-specific
knowledge). This package is the thing built on top of that generic engine
for this one project's specific folder of ~2200 ICO documents.
"""

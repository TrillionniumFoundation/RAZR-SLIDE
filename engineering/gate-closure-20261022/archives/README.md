# Verifiable execution evidence archives

Each package uses ordered 45,000-byte binary segments stored as canonical ASCII base64. Original archives are unchanged. Run python reassemble_base64_archive.py <package>/parts-manifest.json --output <destination.tar.gz>. The script validates every encoded Git blob SHA-1, encoded and decoded SHA-256, lengths, and complete archive SHA-256. It refuses to overwrite an existing output.

The design archive preserves R3 source-gate failure and R4 transitive-input coverage limitation. The verified-mounted-members package contains 64 byte-matched original STEP members and recovery provenance in a newly named container. The final-execution package contains complete frozen final EP5 and EP4 output directories plus the final full-unit evidence ZIP, preserving all failed runs. All physical and manufacturing release gates remain false.

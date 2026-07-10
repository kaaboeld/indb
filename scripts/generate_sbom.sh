#!/bin/bash
# Generate Software Bill of Materials (SBOM) for INDB Backend
# Standard: CycloneDX v1.5 JSON

echo "🔍 Generating SBOM..."

# Ensure cyclonedx-bom is installed
./venv/bin/cyclonedx-py poetry --force || ./venv/bin/cyclonedx-py pip --force --output-format json --output-file bom.json

# If cyclonedx-py fails to detect requirements (since we use pip, not poetry), specify requirements.txt
./venv/bin/cyclonedx-py requirements requirements.txt --output-format json --output-file bom.json

echo "✅ SBOM generated at bom.json"
echo "   Start validation..."
# Simple check
if [ -s bom.json ]; then
    echo "   SBOM size: $(du -h bom.json | cut -f1)"
else
    echo "❌ SBOM generation failed (empty file)"
    exit 1
fi

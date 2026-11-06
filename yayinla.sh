#!/bin/bash
# Minecraft Projesi Otomatik Yayınlama ve Versiyonlama Betiği
set -e
cd "$(dirname "$0")"

# Versiyonu güncelle
python3 - << 'EOF'
import json
try:
    with open("version.json", "r") as f:
        data = json.load(f)
except Exception:
    data = {"major": 0, "minor": 1, "patch": 0, "build": 0}

data["patch"] = data.get("patch", 0) + 1
data["build"] = data.get("build", 0) + 1
new_ver = f"v{data.get('major', 0)}.{data.get('minor', 1)}.{data['patch']}"
data["version"] = new_ver

with open("version.json", "w") as f:
    json.dump(data, f, indent=2)

# index.html içindeki versiyonu güncelle
try:
    with open("index.html", "r") as f:
        html = f.read()
    import re
    html = re.sub(r"const APP_VERSION = '[^']*';", f"const APP_VERSION = '{new_ver}';", html)
    with open("index.html", "w") as f:
        f.write(html)
except Exception as e:
    print("HTML versiyon güncellenemedi:", e)

print(f"Yeni versiyon: {new_ver} (Build #{data['build']})")
EOF

VER=$(python3 -c 'import json; print(json.load(open("version.json"))["version"])')
MSG="${1:-Güncelleme} ($VER)"

git add -A
git commit -m "$MSG"
git push origin main

echo "✅ GitHub'a başarıyla yüklendi: $VER"

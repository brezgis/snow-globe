#!/bin/sh
# Fonts for the bump text cards (both SIL Open Font License). They stay outside the repo.
set -e
D="${SG_BUMP_WORK:-/mnt/ssd240gb/anna/snow-globe-bumps}/fonts"
UA="bump-builder/1.0 (static site build script)"
mkdir -p "$D/inter" && cd "$D"
curl -sSL --fail -A "$UA" -O https://github.com/google/fonts/raw/main/ofl/spacemono/SpaceMono-Bold.ttf
curl -sSL --fail -A "$UA" -O https://github.com/google/fonts/raw/main/ofl/spacemono/SpaceMono-Regular.ttf
curl -sSL --fail -A "$UA" -O https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip
python3 -I -c "
import zipfile
z = zipfile.ZipFile('Inter-4.0.zip')
for n in z.namelist():
    if n.startswith('extras/ttf/Inter-') and n.split('-')[-1] in ('Regular.ttf', 'Medium.ttf', 'SemiBold.ttf', 'Bold.ttf'):
        open('inter/' + n.split('/')[-1], 'wb').write(z.read(n))
"

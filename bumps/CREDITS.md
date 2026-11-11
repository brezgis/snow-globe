# Bump credits

Every bump is 12.000 seconds (1280x720, 24 fps, H.264 + AAC). All text is set in
Inter and Space Mono (SIL Open Font License). All sound is synthesized by
`src/music.py`: there are no recordings, samples or third-party music in any bump.

Licenses below are the ones stated on each source page when the footage was
downloaded on 2026-11-11. `src/fetch_sources.py` records the same information
in a `meta.json` next to each download (outside the repo).

## Archive footage

| bump | source | made by | license | page |
|------|--------|---------|---------|------|
| `sneeze` | Edison Kinetoscopic Record of a Sneeze, January 7, 1894 (Library of Congress print) | W.K.L. Dickson, Edison Manufacturing Co. | Public domain | https://commons.wikimedia.org/wiki/File:Edison_kinetoscopic_record_of_a_sneeze,_January_7,_1894.webm |
| `horse` | The Horse in Motion: Sallie Gardner (1878), animated | Eadweard Muybridge | Public domain | https://commons.wikimedia.org/wiki/File:Horse_in_Motion_-_Sallie_Gardner_(animation).webm |
| `market` | A Trip Down Market Street (1906) | Miles Brothers | Public domain | https://commons.wikimedia.org/wiki/File:A_Trip_down_market_street_(1906).webm |
| `hands` | Master Hands (1936) | Jam Handy Organization for Chevrolet | Public domain | https://commons.wikimedia.org/wiki/File:Master_Hands.webm |
| `bert` | Duck and Cover (1951) | Archer Productions for the U.S. Federal Civil Defense Administration | Public domain (Prelinger Archives) | https://archive.org/details/DuckandC1951 |
| `remote` | Television Remote Control (Tuner) (1961) | Jam Handy Organization | Public domain (Prelinger Archives) | https://archive.org/details/Televisi1961 |
| `jelly` | Jellyfish: 2016 Deepwater Exploration of the Marianas (Okeanos Explorer, dive 4, 24 April 2016) | NOAA Office of Ocean Exploration and Research | Public domain (U.S. government work) | https://commons.wikimedia.org/wiki/File:Jellyfish-_2016_Deepwater_Exploration_of_the_Marianas.webm |
| `orbit` | ISS073-E-1225342-1227437, night pass, 12 November 2025 | NASA Johnson Space Center | Public domain (U.S. government work) | https://commons.wikimedia.org/wiki/File:ISS073-E-1225342-1227437-20251112-Night_-_2025-11-12_ISS073_2096_Night.webm |
| `lava` | Halemaʻumaʻu lava lake, Kīlauea, December 2016 (time-lapse) | U.S. Geological Survey, Hawaiian Volcano Observatory | Public domain (U.S. government work) | https://commons.wikimedia.org/wiki/File:Halema%CA%BBuma%CA%BBu_lava_lake_USGS_multimediaFile-1585.webm |
| `snow` | Snow under LED street light in Tuntorp, Brastad | W.carter | **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). Changes: trimmed, contrast raised, text added. | https://commons.wikimedia.org/wiki/File:Snow_under_LED_street_light_in_Tuntorp,_Brastad.webm |

The footage was trimmed, cropped, graded and captioned. Logos and title cards
that the archives added (Library of Congress, NOAA, USGS) were cut or cropped
out of the picture, which is why they are named here instead.

## Made for the channel

| bump | how |
|------|-----|
| `station`, `tvfield`, `train` | Modelled, lit and rendered in Blender (Cycles) from the scripts in `src/scenes/`. No external models or textures. |
| `ratings`, `twelve`, `clock`, `mail` | Type on black, composed by `src/build.py`. |

## Rebuilding

```
sh bumps/src/fetch_fonts.sh
python3 bumps/src/fetch_sources.py
sh bumps/src/render_all.sh
python3 bumps/src/build.py          # writes bumps/*.mp4, bumps/posters/, bumps/manifest.js
python3 bumps/src/build.py --check  # every file must be exactly 12.000 s
```

Downloads, renders and intermediates live under `$SG_BUMP_WORK`
(default `/mnt/ssd240gb/anna/snow-globe-bumps`), never in the repo.

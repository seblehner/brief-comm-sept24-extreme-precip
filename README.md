# Analysis of the September 2024 Extreme Precipitation Event in Austria

<!-- badges: start -->
<p align="center">
    <a href="https://doi.org/10.5194/egusphere-2026-1825">
        <img alt="Paper DOI" src="https://img.shields.io/badge/preprint-egusphere-darkblue?style=flat-square"></a>
    <a href="https://doi.org/10.5281/zenodo.19346127">
        <img alt="Zenodo data doi" src="https://img.shields.io/badge/data-Zenodo-blue?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBpZD0iU3ZnanNTdmcxMDIxIiB3aWR0aD0iMjg4IiBoZWlnaHQ9IjI4OCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2ZXJzaW9uPSIxLjEiIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB4bWxuczpzdmdqcz0iaHR0cDovL3N2Z2pzLmNvbS9zdmdqcyI%2BPGRlZnMgaWQ9IlN2Z2pzRGVmczEwMjIiPjwvZGVmcz48ZyBpZD0iU3ZnanNHMTAyMyI%2BPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGVuYWJsZS1iYWNrZ3JvdW5kPSJuZXcgMCAwIDIyMCA4MCIgdmlld0JveD0iMCAwIDUxLjA0NiA1MS4wNDYiIHdpZHRoPSIyODgiIGhlaWdodD0iMjg4Ij48cGF0aCBmaWxsPSIjZmZmZmZmIiBkPSJtIDI4LjMyNCwyMC4wNDQgYyAtMC4wNDMsLTAuMTA2IC0wLjA4NCwtMC4yMTQgLTAuMTMxLC0wLjMyIC0wLjcwNywtMS42MDIgLTEuNjU2LC0yLjk5NyAtMi44NDgsLTQuMTkgLTEuMTg4LC0xLjE4NyAtMi41ODIsLTIuMTI1IC00LjE4NCwtMi44MDUgLTEuNjA1LC0wLjY3OCAtMy4zMDksLTEuMDIgLTUuMTA0LC0xLjAyIC0xLjg1LDAgLTMuNTY0LDAuMzQyIC01LjEzNywxLjAyIC0xLjQ2NywwLjYyOCAtMi43NjQsMS40ODggLTMuOTEsMi41NTIgViAxNC44NCBjIDAsLTEuNTU3IC0xLjI2MiwtMi44MjIgLTIuODIsLTIuODIyIGggLTE5Ljc3NSBjIC0xLjU1NywwIC0yLjgyLDEuMjY1IC0yLjgyLDIuODIyIDAsMS41NTkgMS4yNjQsMi44MiAyLjgyLDIuODIgaCAxNS41NDEgbCAtMTguMjMsMjQuNTQ2IGMgLTAuMzYyLDAuNDg3IC0wLjU1NywxLjA3NyAtMC41NTcsMS42ODIgdiAxLjg0MSBjIDAsMS41NTggMS4yNjQsMi44MjIgMi44MjIsMi44MjIgSCA1LjAzOCBjIDEuNDg4LDAgMi43MDUsLTEuMTUzIDIuODEyLC0yLjYxNCAwLjkzMiwwLjc0MyAxLjk2NywxLjM2NCAzLjEwOSwxLjg0OCAxLjYwNSwwLjY4NCAzLjI5OSwxLjAyMSA1LjEwMiwxLjAyMSAyLjcyMywwIDUuMTUsLTAuNzI2IDcuMjg3LC0yLjE4NyAxLjcyNywtMS4xNzYgMy4wOTIsLTIuNjM5IDQuMDg0LC00LjM4OSAwLjgzMjc5OSwtMS40NzIwOTQgMS40MTgyODQsLTIuNjMzMzUyIDEuMjIxODg5LC0zLjcyOTE4MiAtMC4xNzMwMDMsLTAuOTY1MzE4IC0wLjY5NDkxNCwtMS45NDY0MTkgLTIuMzI2ODY1LC0yLjM3ODM1OCAtMC41OCwwIC0xLjM3NjAyNCwwLjE3NDU0IC0xLjgzMzAyNCwwLjQ5MjU0IC0wLjQ2MywwLjMxNiAtMC43OTMsMC43NDQgLTAuOTgyLDEuMjc1IGwgLTAuNDUzLDAuOTMgYyAtMC42MzEsMS4zNjUgLTEuNTY2LDIuNDQzIC0yLjgwOSwzLjI0NCAtMS4yMzgsMC44MDMgLTIuNjMzLDEuMjAxIC00LjE4OCwxLjIwMSAtMS4wMjMsMCAtMi4wMDQsLTAuMTkxIC0yLjk1NSwtMC41NzkgLTAuOTQxLC0wLjM5IC0xLjc1OCwtMC45MzUgLTIuNDM5LC0xLjY0IEMgOS45ODYsNDAuMzQzIDkuNDQxLDM5LjUyNiA5LjAyNywzOC42MDMgOC42MTcsMzcuNjc5IDguNDEsMzYuNzEgOC40MSwzNS42ODcgdiAtMi40NzYgaCAxNy43MTUgYyAwLDAgMS41MTc3NzQsLTAuMTU0NjYgMi4xODMzNzUsLTAuNzcwNjcyIDAuOTU4NDk2LC0wLjg4NzA4NSAwLjg2NDYyMiwtMi4xNTAzOCAwLjg2NDYyMiwtMi4xNTAzOCAwLDAgLTAuMDQzNTQsLTUuMDY2ODM0IC0wLjMzODM3NiwtNy41NzgxNTQgQyAyOC43MjkwNDgsMjEuODEyNTYzIDI4LjMyNCwyMC4wNDQgMjguMzI0LDIwLjA0NCBaIE0gLTExLjc2Nyw0Mi45MSAyLjk5MSwyMy4wMzYgQyAyLjkxMywyMy42MjMgMi44NywyNC4yMiAyLjg3LDI0LjgyNyB2IDEwLjg2IGMgMCwxLjc5OSAwLjM1LDMuNDk4IDEuMDU5LDUuMTA0IDAuMzI4LDAuNzUyIDAuNzE5LDEuNDU4IDEuMTU2LDIuMTE5IC0wLjAxNiwwIC0wLjAzMSwtMTBlLTQgLTAuMDQ3LC0xMGUtNCBIIC0xMS43NjcgWiBNIDIzLjcxLDI3LjY2NyBIIDguNDA5IHYgLTIuODQxIGMgMCwtMS4wMTUgMC4xODksLTEuOTkgMC41OCwtMi45MTIgMC4zOTEsLTAuOTIyIDAuOTM2LC0xLjc0IDEuNjQ1LC0yLjQ0NCAwLjY5NywtMC43MDMgMS41MTYsLTEuMjQ5IDIuNDM4LC0xLjY0MSAwLjkyMiwtMC4zODggMS45MiwtMC41ODEgMi45OSwtMC41ODEgMS4wMiwwIDIuMDAyLDAuMTkzIDIuOTQ5LDAuNTgxIDAuOTQ5LDAuMzkzIDEuNzY0LDAuOTM4IDIuNDQxLDEuNjQxIDAuNjgyLDAuNzA0IDEuMjI1LDEuNTIxIDEuNjQxLDIuNDQ0IDAuNDE0LDAuOTIyIDAuNjE3LDEuODk2IDAuNjE3LDIuOTEyIHoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKDIwLjM1IC00LjczNSkiIGNsYXNzPSJjb2xvcmZmZiBzdmdTaGFwZSI%2BPC9wYXRoPjwvc3ZnPjwvZz48L3N2Zz4%3D"></a>
    <a href="https://github.com/psf/black">
        <img alt="Python code style: black" src="https://img.shields.io/badge/codestyle-black-000000?style=flat-square&logo=Python&logoColor=white"></a>
    <a href="https://style.tidyverse.org">
        <img alt="R code style: tidyverse" src="https://img.shields.io/badge/codestyle-tidyverse-1a162d?style=flat-square&logo=r&logoColor=white"></a>
</p>
<!-- badges: end -->

This repository supplements the manuscript by
Sebastian Lehner <sup>[![](https://info.orcid.org/wp-content/uploads/2020/12/orcid_16x16.gif)](https://orcid.org/0000-0002-7562-8172)</sup>,
Harald Schellander <sup>[![](https://info.orcid.org/wp-content/uploads/2020/12/orcid_16x16.gif)](https://orcid.org/0000-0001-7661-287X)</sup>,
Theresa Schellander-Gorgas <sup>[![](https://info.orcid.org/wp-content/uploads/2020/12/orcid_16x16.gif)](https://orcid.org/0000-0003-3598-2932)</sup>,
Matthias Schlögl <sup>[![](https://info.orcid.org/wp-content/uploads/2020/12/orcid_16x16.gif)](https://orcid.org/0000-0002-4357-523X)</sup> and
Klaus Haslinger <sup>[![](https://info.orcid.org/wp-content/uploads/2020/12/orcid_16x16.gif)](https://orcid.org/0000-0003-2237-9894)</sup> and
(2026):
**Brief communication: Contextualizing the September 2024 extreme precipitation in Austria within the climatological record**.
*EGUsphere* [Preprint]. <!-- Issue(Volume), pp-pp. [doi:](https://doi.org/#).-->

## Repository contents

### Setup

The symbolic link in the root directory of this repository for `dat` and the `DAT_DIR` variable within the `config.toml` need to be set accordingly and are just placeholder. They should point to the path of the data from Zenodo (see below).

### Data (`dat/`)

Data sourced from:

- All source data are precipitation totals with the unit $\left[\text{mm}\cdot\text{day}^{-1}\right]$, or equivalently $\left[\text{kg}\cdot\text{m}^{-2}\cdot\text{day}^{-1}\right]$
- Station data (TAWES):
    - Dataset: https://doi.org/10.60669/gs6w-jd70
    - Station IDs:
    - `[5625,5601,5604,5606,5607,5609,4080,4081,7110,10510,10511,6540,5410,5412,7000,7001,7002,1730,3520]`
    - Note that some stations have multiple IDs due to being slightly relocated over time. The latest ID is used for indexing.
- Gridded data (SPARTACUS):
    - Reference paper: https://doi.org/10.1007/s00704-017-2093-x
    - Dataset: https://doi.org/10.60669/5cqg-p427
- Persistent archive for processed data:
    - Dataset: https://doi.org/10.5281/zenodo.19346127

Processed data within this repository:

- `dat/station_locations.csv`: Station ID and coordinates in degrees (latitude, longitude)
- `dat/station_data.csv`: Unprocessed station data
- `dat/{rps|rls}.{json|csv}`: json output from extreme value analysis (return periods and levels)
- `dat/station_data_pivot.csv`: Pivoted (*wide*[^1]) table of station data (one column per station)
- `dat/station_data_pivot_rx5day.csv`: Rolling 5-day precipitation sums in the same wide format
- `dat/station_data_pivot_rx5day_year.csv`: Rx5day, which is the annual maximum of the rolling 5‑day precipitation sums in the same wide format

### Documents (`doc/`)

- `doc/tab1.tex`: Manuscript Table 1 (`tex`)
- `doc/fig1.png`: Figure 1: Map of 2024 Rx5day, deviation from historical records as [%], and station locations with their corresponding rank for the 12--16th September 2024 precipitation sums
- `doc/fig2.png`: Figure 2: Time series at selected stations with modeled and observed return periods
- `doc/area_affected.log`: logged calculation for % of area affected by new records
- `doc/suppl/`: subfolder containing plots similar to Fig1, but for the major summer floods pf 1997, 2002, 2005, and 2013

![](doc/fig1.png)

![](doc/fig2.png)

### Footnotes

[^1]: "Wide" table format: each station is a separate column, rows are aligned by time/index.

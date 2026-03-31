import json
from pathlib import Path
from types import SimpleNamespace

import cartopy
import cartopy.crs as ccrs
import matplotlib
import matplotlib as mpl
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray
import tomli
import xarray as xr

# internal library for spartacus cmaps
try:
    from gsacmaps import spartacus_RR_mon

    sparta_cmap_fallback = False
except ImportError:
    print("gsacmaps not found. Using fallback cmap.")
    sparta_cmap_fallback = True

from matplotlib import ticker
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

stationnum2name = {
    "5625": "Lilienfeld-Tarschberg",
    "5600": "St. Pölten-Landhaus",
    "5601": "St. Pölten-Landhaus",
    "5602": "St. Pölten-Landhaus",
    "5603": "St. Pölten-Landhaus",
    "5604": "St. Pölten-Landhaus",
    "5605": "St. Pölten-Landhaus",
    "5606": "St. Pölten-Landhaus",
    "5607": "St. Pölten-Landhaus",
    "5608": "St. Pölten-Landhaus",
    "5609": "St. Pölten-Landhaus",
    "4080": "Langenlebarn",
    "4081": "Langenlebarn",
    "7110": "Lunz am See",
    "10510": "Reichenau an der Rax",
    "10511": "Reichenau an der Rax",
    "6540": "Unterach am Attersee",
    "5410": "Oberndorf-Melk",
    "5412": "Oberndorf-Melk",
    "7000": "Weyer",
    "7001": "Weyer",
    "7002": "Weyer",
    "1730": "Schwarzau im Freiwald",
    "3520": "Baernkopf",
}

stationname2num = {
    "Lilienfeld-Tarschberg": "5625",
    "St. Pölten-Landhaus": "5609",
    "Langenlebarn": "4081",
    "Lunz am See": "7110",
    "Reichenau an der Rax": "10511",
    "Unterach am Attersee": "6540",
    "Oberndorf-Melk": "5412",
    "Weyer": "7002",
    "Schwarzau im Freiwald": "1730",
    "Baernkopf": "3520",
}

stationnum2rank = {
    "5625": "1",
    "5609": "2",
    "4081": "3",
    "7110": "4",
    "10511": "5",
    "6540": "6",
    "5412": "7",
    "7002": "8",
    "1730": "9",
    "3520": "10",
}


def make_sparta_cmap():
    def _build_cmap(colors, lower_boundary):
        import matplotlib as mpl

        cmap, norm = mpl.colors.from_levels_and_colors(
            levels=lower_boundary, colors=colors, extend="max"
        )
        return cmap, norm

    colors = [
        "#F7F7F7",
        "#FFFFD9",
        "#EDF8B1",
        "#C7E9B4",
        "#7FCDBB",
        "#41B6C4",
        "#1D91C0",
        "#185EA8",
        "#003CA6",
        "#574995",
        "#922E83",
        "#BA2049",
        "#E55649",
    ]
    lower_boundary = [
        0.0,
        2.0,
        15.0,
        30.0,
        50.0,
        75.0,
        100.0,
        150.0,
        200.0,
        250.0,
        350.0,
        450.0,
        600.0,
    ]
    cmap_, norm_ = _build_cmap(colors, lower_boundary)
    return cmap_, norm_


def configure_font():
    # Configure default plotting font to 'Source Sans 3' (preferred) with a
    # graceful fallback. If the font is available in the system font list it is
    # prepended to the sans-serif rcParam so matplotlib will use it for plots.
    # If the font is not found a warning is emitted but execution continues and
    # matplotlib will fall back to the next available sans-serif font.
    # source: https://fonts.adobe.com/fonts/source-sans-3
    _climind_preferred_font = "Source Sans 3"
    # Note: the following 2 lines manually add for user-installed fonts
    # in ~/.local/share/fonts in case they are not found in the system
    for fontfile in Path(Path.home(), ".local/share/fonts/").glob("*.ttf"):
        font_manager.fontManager.addfont(str(fontfile))
    _available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    if _climind_preferred_font in _available_fonts:
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = [
            _climind_preferred_font,
        ] + matplotlib.rcParams.get("font.sans-serif", [])
        matplotlib.rcParams["font.size"] = 12
    else:
        # still prepend so if the font gets installed later it will be preferred
        matplotlib.rcParams["font.sans-serif"] = [
            _climind_preferred_font,
        ] + matplotlib.rcParams.get("font.sans-serif", [])
        print(
            f"Font '{_climind_preferred_font}' not found in system fonts. Plots will use a fallback sans-serif font until it's installed."
        )
    return None


def get_config(conf_file: str = "config.toml", out_type: str = "namespace") -> dict:
    """Load config params from toml config file.

    Args:
        conf_file (str, optional): Path to config file. Defaults to "config.toml".
        out_type (str, optional): Output type for config, either 'dict', or 'namespace'.
            'dict' returns the config as nested dictionary, while 'namespace' returns
            a nested SimpleNamespace, allowing for '.' syntax to acces attributes.
            Defaults to "namespace".

    Returns:
        dict: config dict
    """

    def _dict_to_recursive_namespace(dict_: dict) -> SimpleNamespace:
        """Convenience function to transform a dictionary into a recursive
        SimpleNamespace to allow for '.' syntax to access attributes.

        Args:
            dict_ (dict): dictionary which is to be transformed

        Returns:
            namespace (SimpleNamespace): dictionary transformed into a SimpleNamespace
        """
        return json.loads(
            json.dumps(dict_), object_hook=lambda item: SimpleNamespace(**item)
        )

    with open(conf_file, "rb") as file:
        config = tomli.load(file)
        if out_type == "namespace":
            config = _dict_to_recursive_namespace(dict_=config)
    return config


def add_cartopy_styling(
    ax_: matplotlib.axes.Axes, gridlines: bool = True, drawlabel: bool = True
) -> matplotlib.lines.Line2D:
    """add cartopy specific styling for spatial map plots

    Args:
        ax_ (matplotlib.axes.Axes): axis to modify
        gridlines (bool, optional): draw gridlines. Defaults to True.
        drawlabel (bool, optional): draw labels. Defaults to True.

    Returns:
        matplotlib.lines.Line2D: gridlines object
    """
    gl = None
    ax_.add_feature(cartopy.feature.LAND, color="#e2d9c3")
    ax_.add_feature(cartopy.feature.OCEAN)
    ax_.add_feature(cartopy.feature.COASTLINE)
    ax_.add_feature(cartopy.feature.BORDERS, linestyle="-")
    if gridlines:
        gl = ax_.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=drawlabel,
            linewidth=1,
            color="gray",
            alpha=0.5,
            linestyle="--",
            x_inline=False,
            rotate_labels=False,
        )
    ax_.set_extent([9.3, 17.3, 46, 49.2])
    return gl


def plt_composite_maps(
    xda_rx5day_2024: xr.DataArray,
    percentage_2024_vs_clim: xr.DataArray,
    titlestr_1: str = "Rx5day 2024",
    titlestr_2: str = "Deviation for Rx5day in 2024 from historic Rx5day (1961–2023)",
    savefile: str = "test.png",
) -> None:
    # projection for EPSG:3416
    cartopy_proj = {
        "projection": cartopy.crs.LambertConformal(
            central_longitude=13.3333333,
            central_latitude=47.5,
            false_easting=400000,
            false_northing=400000,
            standard_parallels=(49, 46),
        )
    }

    if sparta_cmap_fallback:
        print("Using fallback cmap for spartacus data.")
        sparta_cmap, sparta_norm = make_sparta_cmap()
    else:
        sparta_cmap, sparta_norm = spartacus_RR_mon

    fig = plt.figure(figsize=(18, 7), constrained_layout=True)
    gs = fig.add_gridspec(ncols=2)
    ax_left = fig.add_subplot(gs[0], **cartopy_proj)
    ax_right = fig.add_subplot(gs[1], **cartopy_proj)

    # discretize cmaps
    cmap1 = plt.cm.Blues
    cmaplist1 = [cmap1(i) for i in range(cmap1.N)]
    cmapnew1 = mpl.colors.LinearSegmentedColormap.from_list(
        "Custom cmap",
        cmaplist1[5:],
        cmap1.N,
    )
    bounds1 = np.linspace(100, 250, 7)
    norm1 = mpl.colors.BoundaryNorm(bounds1, cmap1.N, extend="both")

    axes = [ax_left, ax_right]
    for idx, (
        ax,
        xdaiter,
        subplotnum,
        titlestr,
        clabels,
        cbarori,
        cmap,
        cmap_norm,
        cshrink,
    ) in enumerate(
        zip(
            iter(axes),
            [xda_rx5day_2024, percentage_2024_vs_clim],
            ["a)", "b)"],
            [
                titlestr_1,
                titlestr_2,
            ],
            [
                "Rx5day [mm]",
                "Deviation [%]",
            ],
            [
                "horizontal",
                "horizontal",
            ],
            [sparta_cmap, cmapnew1],
            [sparta_norm, norm1],
            [1, 1],
        )
    ):
        gl = add_cartopy_styling(ax)
        if idx == 0:
            gl.right_labels = False
        elif idx == 1:
            gl.left_labels = False

        if idx == 0:
            cax = inset_axes(
                ax,
                width="45%",
                height="6%",
                loc="upper left",
                bbox_to_anchor=(0.02, -0.05, 1, 1),
                bbox_transform=ax.transAxes,
            )
            xdaiter.plot(
                ax=ax,
                cbar_kwargs={
                    "orientation": cbarori,
                    "label": clabels,
                    "shrink": cshrink,
                    "cax": cax,
                    "ticks": sparta_norm.boundaries,
                },
                cmap=cmap,
                norm=cmap_norm,
            )

            # add stations as annotated points
            df_loc = pd.read_csv("dat/station_locations.csv", sep=";")
            ax.scatter(
                df_loc["lon"],
                df_loc["lat"],
                transform=ccrs.PlateCarree(),
                color="C1",
                s=100,
                marker="o",
                edgecolor="white",
                linewidth=0.5,
                zorder=20,
            )
            for stationnum in df_loc["statnr"].values:
                x, y = (
                    df_loc.query(f"statnr == {stationnum}")["lon"].values[0],
                    df_loc.query(f"statnr == {stationnum}")["lat"].values[0],
                )
                ax.annotate(
                    stationnum2rank[str(stationnum)],
                    xy=(x, y),
                    xycoords=ccrs.PlateCarree(),
                    xytext=(x + 0.2, y + 0.05),
                    textcoords=ccrs.PlateCarree(),
                    arrowprops=dict(arrowstyle="-", color="white", lw=1),
                    fontsize="x-large",
                    fontweight="bold",
                    color="white",
                )

        else:
            cax = inset_axes(
                ax,
                width="45%",
                height="6%",
                loc="upper left",
                bbox_to_anchor=(0.02, -0.05, 1, 1),
                bbox_transform=ax.transAxes,
            )
            xdaiter.plot(
                ax=ax,
                cbar_kwargs={
                    "orientation": cbarori,
                    "label": clabels,
                    "shrink": cshrink,
                    "cax": cax,
                    "ticks": cmap_norm.boundaries,
                },
                cmap=cmap,
                norm=cmap_norm,
                # center=0,
            )

            def stats_increase(xda_, thresh):
                per_increase = round(
                    float(
                        xda_.where(xda_ > thresh, np.nan).count().values
                        / xda_.count().values
                        * 100
                    ),
                    2,
                )
                return per_increase

            area_affected_list = [
                "#" * 30,
                "Percentage of grid cells with an increase in Rx5day over historical max:",
                titlestr_1,
                f"Any increase (any new records): {stats_increase(xdaiter, 100)} %",
                f"More than 1.5 times the hist max: {stats_increase(xdaiter, 150)} %",
                f"More than double the hist max: {stats_increase(xdaiter, 200)} %",
                f"Grid cell with max % increase: {round(float(xdaiter.max().values - 100), 2)} %",
                "#" * 30,
            ]
            area_affected_str = "\n".join(area_affected_list) + "\n"
            print(area_affected_str)
            with open(arealogpath, "a") as file:
                file.write(area_affected_str)

        ax.set_title(titlestr)

        ax.text(
            0,
            1,
            subplotnum,
            transform=ax.transAxes,
            fontsize="x-large",
            fontweight="bold",
            va="top",
            ha="left",
            clip_on=True,
            bbox={"facecolor": "w", "pad": 5},
        )
    plt.savefig(savefile, bbox_inches="tight", dpi=300)
    plt.close()
    return None


def plot_timeseries(
    df_rx5d: pd.DataFrame,
    rp_obs: pd.DataFrame,
    return_levels: pd.DataFrame,
    modelled_rp: pd.DataFrame,
    cols: list[str],
):
    df_rx5d.index = df_rx5d.index.year
    ts1 = df_rx5d[cols[0]].dropna()
    ts2 = df_rx5d[cols[1]].dropna()
    ts3 = df_rx5d[cols[2]].dropna()
    years1 = ts1.index
    years2 = ts2.index
    years3 = ts3.index
    rp1 = rp_obs.query(f"station == '{cols[0]}'")
    rl1 = return_levels.query(f"station == '{cols[0]}'")
    rp2 = rp_obs.query(f"station == '{cols[1]}'")
    rl2 = return_levels.query(f"station == '{cols[1]}'")
    rp3 = rp_obs.query(f"station == '{cols[2]}'")
    rl3 = return_levels.query(f"station == '{cols[2]}'")
    mod_rp1 = modelled_rp.query(f"station == '{cols[0]}'")
    mod_rp2 = modelled_rp.query(f"station == '{cols[1]}'")
    mod_rp3 = modelled_rp.query(f"station == '{cols[2]}'")
    _, axes = plt.subplots(figsize=(10, 7), ncols=2, sharey=True, sharex="col", nrows=3)
    for idx, ts, years, rp, rl, mod_rp, subplot_num in zip(
        range(3),
        [ts1, ts2, ts3],
        [years1, years2, years3],
        [rp1, rp2, rp3],
        [rl1, rl2, rl3],
        [mod_rp1, mod_rp2, mod_rp3],
        [("a)", "b)"), ("c)", "d)"), ("e)", "f)")],
    ):
        ax1 = axes[idx, 0]
        ax2 = axes[idx, 1]

        ax1.bar(years[:-1], ts.iloc[:-1], color="C0", width=0.8)
        ax1.bar(years[-1], ts.iloc[-1], color="C1", width=0.8, label="2024")
        ax1.set_title(f"Station: {ts.name}")
        ax1.set_ylabel("Rx5day [mm]")
        ax1.grid(linewidth=0.5)
        ax1.set_xlim(1900, 2026)

        ax2.plot(
            rl["return_period"], rl["median"], color="k", label="Modelled return level"
        )
        ax2.fill_between(
            rl["return_period"],
            rl["lower_ci"],
            rl["upper_ci"],
            color="k",
            alpha=0.2,
            label="95% confidence interval",
        )
        ax2.plot(
            rl["return_period"], rl["lower_ci"], color="C0", linestyle="--", lw=0.75
        )
        ax2.plot(
            rl["return_period"], rl["upper_ci"], color="C0", linestyle="--", lw=0.75
        )
        ax2.scatter(x=rp["rp_obs"], y=rp["rl_obs"], s=30)

        rp2024 = rp["rp_obs"].max()
        rl2024 = rp["rl_obs"].max()
        ax2.scatter(x=rp2024, y=rl2024, s=60, marker="*", color="C1", zorder=20)
        mod_rp_2024 = mod_rp["rp_median"].max()
        ax2.set_title(f"Estimated return period for 2024: {mod_rp_2024:.0f} years")
        ax2.set_ylabel("")
        ax2.grid(linewidth=0.5)
        ax2.set_xscale("log")
        ax2.xaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
        ax1.set_ylim(0, 430)
        ax2.set_xlim(0.9, 1100)

        if idx < 2:
            ax2.set_xlabel("")
        if idx == 2:
            ax1.set_xlabel("Year")
            ax2.set_xlabel("Return Period [years]")

        for axi, num in zip([ax1, ax2], subplot_num):
            axi.text(
                0.005,
                0.99,
                num,
                transform=axi.transAxes,
                fontsize="medium",
                fontweight="bold",
                va="top",
                ha="left",
                clip_on=True,
                bbox={"facecolor": "w", "pad": 2},
            )
    plt.subplots_adjust(wspace=0.05)
    plt.suptitle("Rx5day: Maximum annual 5-day precipitation totals")
    plt.savefig("doc/fig2.png", bbox_inches="tight", dpi=300)
    return None


if __name__ == "__main__":
    config = get_config()
    epsg = config.CRS.EPSG
    configure_font()
    data_dir = Path(config.PATHS.DAT_DIR)

    if config.PLOT.COMPOSITE:
        year_start = config.GENERAL.YEAR_START
        year_end = config.GENERAL.YEAR_END
        rx5_sparta_file = Path(data_dir, config.PATHS.FILE_RX5DAY)
        arealogpath = Path(config.PATHS.LOGAREA)

        rx5_sparta = xr.open_dataarray(rx5_sparta_file)
        histmax = rx5_sparta.sel(time=slice(str(year_start), str(year_end - 1))).max(
            dim="time"
        )
        histmax = histmax.rio.write_crs(epsg)
        rx5_2024 = rx5_sparta.sel(time=f"{year_end}-01-01")
        rx5_2024 = rx5_2024.rio.write_crs(epsg)

        if arealogpath.exists():
            arealogpath.unlink()
        else:
            arealogpath.touch()

        percentage_vs_histmax = 100 / histmax * rx5_2024
        plt_composite_maps(
            xda_rx5day_2024=rx5_2024,
            percentage_2024_vs_clim=percentage_vs_histmax,
            savefile="doc/fig1.png",
        )

        ## check area % increases for major summer floods: 1997, 2002, 2005, 2013
        major_flood_years = [1997, 2002, 2005, 2013]
        for year_iter in major_flood_years:
            past_histmax = rx5_sparta.sel(
                time=slice(str(year_start), str(year_iter - 1))
            ).max(dim="time")
            rx5_flood = rx5_sparta.sel(time=str(year_iter))
            percentage_flood = 100 / past_histmax * rx5_flood
            plt_composite_maps(
                xda_rx5day_2024=rx5_flood,
                percentage_2024_vs_clim=percentage_flood,
                titlestr_1=f"Rx5day {year_iter}",
                titlestr_2=f"Deviation for Rx5day in {year_iter} from historic Rx5day (1961–{year_iter - 1})",
                savefile=f"doc/suppl/fig_suppl_flood_{year_iter}.png",
            )

    if config.PLOT.TIMESERIES:
        df = pd.read_csv(str(Path(data_dir, "station_data.csv")), sep=";")
        df["nied [mm]"] = df["nied [mm]"].astype(float)
        df.loc[df["nied [mm]"] == -1, "nied [mm]"] = 0
        df.loc[df["nied [mm]"] == 9999, "nied [mm]"] = np.nan
        df["stationname"] = df["istnr"].map(lambda x: stationnum2name[str(x)])
        df["name_id"] = [
            f"{stationname}_{stationname2num[stationname]}"
            for stationname in df["stationname"].values
        ]
        with open(str(Path(data_dir, "rps.json")), "r") as f:
            rps = json.load(f)
        with open(str(Path(data_dir, "rls.json")), "r") as f:
            rls = json.load(f)

        dfrp_list = []
        for stationname, content in rps.items():
            dfrp_iter = pd.DataFrame(content)
            dfrp_list.append(dfrp_iter)
        dfrp = pd.concat(dfrp_list, ignore_index=True)
        dfrp.to_csv("dat/rps.csv", index=False)

        dfrl_list = []
        mod_obs_list = []
        emp_obs_list = []
        for stationname, content in rls.items():
            dfrl_iter = pd.DataFrame(content["rls"])
            dfrl_list.append(dfrl_iter)
            dfmo_iter = pd.DataFrame(content["modeled_obs"])
            mod_obs_list.append(dfmo_iter)
            dfeo_iter = pd.DataFrame(content["empirical_obs"])
            dfeo_iter["station"] = stationname
            emp_obs_list.append(dfeo_iter)
        dfrl = pd.concat(dfrl_list, ignore_index=True)
        dfmo = pd.concat(mod_obs_list, ignore_index=True)
        dfeo = pd.concat(emp_obs_list, ignore_index=True)
        dfrl.to_csv(str(Path(data_dir, "rls.csv")), index=False)
        dfmo.to_csv(str(Path(data_dir, "modeled_obs.csv")), index=False)
        dfeo.to_csv(str(Path(data_dir, "empirical_obs.csv")), index=False)

        df["date"] = pd.to_datetime(df["datum"], format="%d.%m.%Y")
        dfpivot = df.pivot(index="date", columns="name_id", values="nied [mm]")
        dfpivot.to_csv(
            str(Path(data_dir, "station_data_pivot.csv")),
            index_label="date",
            na_rep="9999",
            float_format="%.1f",
        )
        ts4corr = dfpivot.rolling(window=5).sum()
        ts4corr.to_csv(
            str(Path(data_dir, "station_data_pivot_rx5day.csv")),
            index_label="date",
            na_rep="9999",
            float_format="%.1f",
        )
        rx5day_year = ts4corr.resample("YE").max()
        rx5day_year.to_csv(
            str(Path(data_dir, "station_data_pivot_rx5day_year.csv")),
            index_label="date",
            na_rep="9999",
            float_format="%.1f",
        )
        print("#" * 30)
        print("Stationname \t\t length years \t Estimated rp 2024")
        for station in rx5day_year.columns:
            print(
                f"{station}: \t\t {rx5day_year[station].dropna().index[-1].year - rx5day_year[station].dropna().index[0].year + 1}"
                f" \t\t {dfmo.query(f'station == "{station}"')['rp_median'].max():1.0f}"
                f" ({dfmo.query(f'station == "{station}"')['rp_lower_ci95'].max():1.0f}"
                f"–{dfmo.query(f'station == "{station}"')['rp_upper_ci95'].max():1.0f})"
            )
        print("#" * 30)
        station_plots = [
            "St. Pölten-Landhaus_5609",
            "Langenlebarn_4081",
            "Reichenau an der Rax_10511",
        ]

        plot_timeseries(rx5day_year, dfeo, dfrl, dfmo, cols=station_plots)

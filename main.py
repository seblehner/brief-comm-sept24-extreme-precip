import json
from pathlib import Path
from types import SimpleNamespace

import cartopy
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tomli
import xarray as xr
from matplotlib import font_manager

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


# area of interest and projection for the synoptic overview map (Europe)
SYNOPTIC_EXTENT = [-12.0, 40.0, 34.0, 63.0]
SYNOPTIC_PROJ = {
    "projection": cartopy.crs.LambertConformal(
        central_longitude=14,
        central_latitude=50,
        standard_parallels=(40, 60),
    )
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


def load_era5_field(
    file_: str, varname: str, date: str, extent: list[float], margin: float = 15.0
) -> xr.DataArray:
    """Load a single day of an ERA5 field and cut it to the area of interest.

    ERA5 is stored on a 0–360° longitude grid with decreasing latitudes, so
    longitudes are shifted to -180–180° and the latitude slice is reversed.
    The cutout is padded by 'margin' degrees so that the projected map extent
    is fully covered by data.

    Args:
        file_ (str): path to the ERA5 netCDF file
        varname (str): name of the variable to read (e.g. 'z', 'tcwv')
        date (str): date to select, e.g. '2024-09-14'
        extent (list[float]): [lon_min, lon_max, lat_min, lat_max] in degrees
        margin (float, optional): padding around the extent in degrees.
            Defaults to 15.0.

    Returns:
        xr.DataArray: 2D field (latitude, longitude) for the requested date
    """
    lon_min, lon_max, lat_min, lat_max = extent
    xda = xr.open_dataset(file_)[varname].sel(time=date).squeeze(drop=True)
    xda = xda.assign_coords(longitude=(((xda["longitude"] + 180) % 360) - 180)).sortby(
        "longitude"
    )
    xda = xda.sel(
        longitude=slice(lon_min - margin, lon_max + margin),
        latitude=slice(lat_max + margin, lat_min - margin),
    )
    return xda.load()


def get_country_geometry(country: str = "Austria"):
    """Return the Natural Earth (10m) polygon of a country.

    Args:
        country (str, optional): country name as in the 'ADMIN' attribute.
            Defaults to "Austria".

    Returns:
        shapely geometry or None: country outline, None if the country is
            not found in the shapefile
    """
    shpfile = shpreader.natural_earth(
        resolution="10m", category="cultural", name="admin_0_countries"
    )
    for record in shpreader.Reader(shpfile).records():
        if record.attributes.get("ADMIN") == country:
            return record.geometry
    print(f"Country '{country}' not found in Natural Earth shapefile.")
    return None


def plt_synoptic_map(
    xda_z500: xr.DataArray,
    xda_tcwv: xr.DataArray,
    ax_: matplotlib.axes.Axes | None = None,
    extent: list[float] = SYNOPTIC_EXTENT,
    date_label: str = "2024-09-14",
    titlestr: str = "Synoptic situation",
    subplotnum: str | None = None,
    clabel: str = "Total column water vapour [kg m$^{-2}$]",
    savefile: str | None = None,
) -> matplotlib.axes.Axes:
    """Plot 500 hPa geopotential height (contours) over total column water
    vapour (shading) for one day.

    Args:
        xda_z500 (xr.DataArray): geopotential at 500 hPa [m2 s-2]
        xda_tcwv (xr.DataArray): total column water vapour [kg m-2]
        ax_ (matplotlib.axes.Axes | None, optional): axis to draw into. If None
            a standalone figure is created. Defaults to None.
        extent (list[float], optional): [lon_min, lon_max, lat_min, lat_max].
            Defaults to SYNOPTIC_EXTENT.
        date_label (str, optional): date shown in the upper right box.
        titlestr (str, optional): axis title.
        subplotnum (str | None, optional): subplot label, e.g. 'a)'. Defaults to None.
        clabel (str, optional): colorbar label.
        savefile (str | None, optional): if given (and ax_ is None) the figure
            is written to this path. Defaults to None.

    Returns:
        matplotlib.axes.Axes: the axis the map was drawn into
    """
    standalone = ax_ is None
    if standalone:
        fig = plt.figure(figsize=(9, 7), constrained_layout=True)
        ax_ = fig.add_subplot(1, 1, 1, projection=SYNOPTIC_PROJ["projection"])

    ax_.set_extent(extent, crs=ccrs.PlateCarree())
    ax_.add_feature(cartopy.feature.LAND, color="#d9d9d9", zorder=1)
    ax_.add_feature(cartopy.feature.OCEAN, color="white", zorder=1)
    # coastlines and borders are drawn on top of the shading
    ax_.add_feature(cartopy.feature.COASTLINE, linewidth=0.5, zorder=5)
    ax_.add_feature(cartopy.feature.BORDERS, linestyle="-", linewidth=0.3, zorder=5)
    gl = ax_.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=1,
        color="gray",
        alpha=0.5,
        linestyle="--",
        x_inline=False,
        rotate_labels=False,
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlocator = ticker.FixedLocator(np.arange(-20, 61, 10))
    gl.ylocator = ticker.FixedLocator(np.arange(30, 61, 5))

    # total column water vapour as shading, values below the lowest level stay
    # unfilled so that the land/ocean background remains visible
    cmap_tcwv = plt.cm.BuGn
    bounds_tcwv = np.arange(20, 41, 2)
    norm_tcwv = mpl.colors.BoundaryNorm(bounds_tcwv, cmap_tcwv.N, extend="max")
    cf = ax_.contourf(
        xda_tcwv["longitude"],
        xda_tcwv["latitude"],
        xda_tcwv,
        levels=bounds_tcwv,
        cmap=cmap_tcwv,
        norm=norm_tcwv,
        extend="max",
        transform=ccrs.PlateCarree(),
        zorder=2,
    )

    # geopotential height at 500 hPa as contour lines
    gph = xda_z500 / 9.80665
    cs = ax_.contour(
        gph["longitude"],
        gph["latitude"],
        gph,
        levels=np.arange(4800, 6041, 40),
        colors="k",
        linewidths=0.8,
        transform=ccrs.PlateCarree(),
        zorder=3,
    )
    ax_.clabel(cs, inline=True, fontsize="small", fmt="%.0f")

    # highlight the area of interest
    geom_austria = get_country_geometry("Austria")
    if geom_austria is not None:
        ax_.add_geometries(
            [geom_austria],
            crs=ccrs.PlateCarree(),
            facecolor="none",
            edgecolor="red",
            linewidth=1.5,
            zorder=10,
        )

    # white backdrop so the colorbar stays legible on top of the shading
    ax_.add_patch(
        mpl.patches.Rectangle(
            (0.0, 0.0),
            0.49,
            0.15,
            transform=ax_.transAxes,
            facecolor="white",
            edgecolor="k",
            zorder=15,
        )
    )
    cax = inset_axes(
        ax_,
        width="45%",
        height="4%",
        loc="lower left",
        bbox_to_anchor=(0.015, 0.07, 1, 1),
        bbox_transform=ax_.transAxes,
    )
    cbar = plt.colorbar(
        cf,
        cax=cax,
        orientation="horizontal",
        label=clabel,
        ticks=bounds_tcwv,
    )
    cbar.ax.tick_params(labelsize="small")
    cbar.set_label(clabel, size="small")

    ax_.text(
        0.991,
        0.987,
        date_label,
        transform=ax_.transAxes,
        fontsize="large",
        va="top",
        ha="right",
        zorder=20,
        bbox={"facecolor": "w", "pad": 5},
    )
    ax_.set_title(titlestr)
    if subplotnum is not None:
        ax_.text(
            0,
            1,
            subplotnum,
            transform=ax_.transAxes,
            fontsize="x-large",
            fontweight="bold",
            va="top",
            ha="left",
            clip_on=True,
            zorder=20,
            bbox={"facecolor": "w", "pad": 5},
        )

    if standalone and savefile is not None:
        plt.savefig(savefile, bbox_inches="tight", dpi=300)
        plt.close()
    return ax_


def match_axes_height(
    ax_target: matplotlib.axes.Axes, ax_ref: matplotlib.axes.Axes
) -> None:
    """Crop the y-extent of a map axis so it is rendered with the same height
    as a reference map axis.

    Both axes keep a fixed data aspect and fill the same column width, so equal
    height means an equal ratio of projected y- to x-extent. Only the y-limits
    are changed, i.e. the map is cropped and not distorted.

    Args:
        ax_target (matplotlib.axes.Axes): axis that is cropped
        ax_ref (matplotlib.axes.Axes): axis whose height is matched
    """
    x0_ref, x1_ref = ax_ref.get_xlim()
    y0_ref, y1_ref = ax_ref.get_ylim()
    ratio_ref = abs(y1_ref - y0_ref) / abs(x1_ref - x0_ref)
    x0, x1 = ax_target.get_xlim()
    y0, y1 = ax_target.get_ylim()
    height = abs(x1 - x0) * ratio_ref
    ymid = 0.5 * (y0 + y1)
    ax_target.set_ylim(ymid - height / 2, ymid + height / 2)


def plt_composite_maps(
    xda_rx5day_2024: xr.DataArray,
    percentage_2024_vs_clim: xr.DataArray,
    titlestr_1: str = "Rx5day 2024",
    titlestr_2: str = "Deviation for Rx5day in 2024 from historic Rx5day (1961–2023)",
    savefile: str = "test.png",
    clabel_1: str = "Rx5day [mm]",
    clabel_2: str = "Deviation [%]",
    synoptic: dict | None = None,
    logpath: Path | None = None,
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

    # the synoptic overview is prepended as an additional first panel
    ncols = 3 if synoptic is not None else 2
    fig = plt.figure(figsize=(9 * ncols, 7), constrained_layout=True)
    gs = fig.add_gridspec(ncols=ncols)
    col_offset = 0
    subplotnums = ["a)", "b)"]
    if synoptic is not None:
        ax_synop = fig.add_subplot(gs[0], **SYNOPTIC_PROJ)
        plt_synoptic_map(ax_=ax_synop, subplotnum="a)", **synoptic)
        col_offset = 1
        subplotnums = ["b)", "c)"]
    ax_left = fig.add_subplot(gs[col_offset], **cartopy_proj)
    ax_right = fig.add_subplot(gs[col_offset + 1], **cartopy_proj)

    # discretize cmaps
    cmap1 = plt.cm.Blues
    cmaplist1 = [cmap1(i) for i in range(cmap1.N)]
    cmapnew1 = mpl.colors.LinearSegmentedColormap.from_list(
        "Custom cmap",
        cmaplist1[5:],
        cmap1.N,
    )
    bounds1 = np.linspace(0, 150, 7)
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
            subplotnums,
            [
                titlestr_1,
                titlestr_2,
            ],
            [
                clabel_1,
                clabel_2,
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
                f"Any increase (any new records): {stats_increase(xdaiter, 0)} %",
                f"More than 1.5 times the hist max: {stats_increase(xdaiter, 50)} %",
                f"More than double the hist max: {stats_increase(xdaiter, 100)} %",
                f"Grid cell with max % increase: {round(float(xdaiter.max().values), 2)} %",
                "#" * 30,
            ]
            area_affected_str = "\n".join(area_affected_list) + "\n"
            print(area_affected_str)
            with open(logpath if logpath is not None else arealogpath, "a") as file:
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
    if synoptic is not None:
        # crop the synoptic map to the height of the precipitation panels
        match_axes_height(ax_synop, ax_left)
    plt.savefig(savefile, bbox_inches="tight", dpi=300)
    plt.close()


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
        ax1.set_title(f"Station: {ts.name.split('_')[0]}")
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
        ax2.scatter(x=rp2024, y=rl2024, color="C1", zorder=20)
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


def calc_percentage_change(xda1, ref):
    percentage_change = 100 * (xda1 - ref) / ref
    return percentage_change


def get_experiment_paths(config, data_dir: Path) -> SimpleNamespace:
    """Resolve input files, log file, variable name and output dir for the
    currently active experiment in the config.

    Args:
        config: config namespace as returned by get_config()
        data_dir (Path): base directory of the SPARTACUS data

    Returns:
        SimpleNamespace: rx5_file, event_file, arealogpath, varname, outpath
    """
    if config.EXPERIMENT.SPARTAV21RRhr:
        paths = config.PATHS.SPARTAV21RRhr
        varname = "RRhr"
        outdir = "sparta_v2.1_RRhr"
    elif config.EXPERIMENT.SPARTAV3RR:
        paths = config.PATHS.SPARTAV3RR
        varname = "RR"
        outdir = "sparta_v3_RR"
    elif config.EXPERIMENT.SPARTAV3RRhr:
        paths = config.PATHS.SPARTAV3RRhr
        varname = "RRhr"
        outdir = "sparta_v3_RRhr"
    else:
        raise ValueError("No experiment enabled in [EXPERIMENT] section of config.")
    return SimpleNamespace(
        rx5_file=Path(data_dir, paths.FILE_RX5DAY),
        event_file=Path(data_dir, paths.FILE_EVENT_RRhr),
        arealogpath=Path(paths.LOGAREA),
        varname=varname,
        outpath=Path("doc", outdir),
    )


def load_composite_fields(
    config, data_dir: Path, epsg: str
) -> tuple[xr.DataArray, xr.DataArray]:
    """Load the 2024 event totals and their deviation from the historic Rx5day
    maximum for the active experiment.

    Args:
        config: config namespace as returned by get_config()
        data_dir (Path): base directory of the SPARTACUS data
        epsg (str): EPSG code written to the data arrays

    Returns:
        tuple[xr.DataArray, xr.DataArray]: event totals 2024, deviation in %
    """
    exp = get_experiment_paths(config, data_dir)
    histmax = (
        xr.open_dataarray(exp.rx5_file)
        .sel(
            time=slice(str(config.GENERAL.YEAR_START), str(config.GENERAL.YEAR_END - 1))
        )
        .max(dim="time")
        .rio.write_crs(epsg)
    )
    event_2024 = xr.open_dataset(exp.event_file)[exp.varname].rio.write_crs(epsg)
    return event_2024, calc_percentage_change(event_2024, histmax)


if __name__ == "__main__":
    config = get_config()
    epsg = config.CRS.EPSG
    configure_font()
    data_dir = Path(config.PATHS.DAT_DIR)

    if config.PLOT.PREPROCESS:
        # extract event precip from spartacus
        rrhr2024 = xr.open_dataset(
            Path(data_dir, config.PATHS.FILE_SPARTA_RRhr_2024)
        ).sel(time=slice("2024-09-12", "2024-09-16"))["RRhr"]
        event_5day_totals = rrhr2024.sum(dim="time")
        event_5day_totals = event_5day_totals.where(
            rrhr2024.isel(time=0).notnull(), np.nan
        )
        event_5day_totals.rio.write_crs(epsg).to_netcdf(
            Path(data_dir, config.PATHS.FILE_EVENT_RRhr)
        )

    if config.PLOT.COMPOSITE:
        year_start = config.GENERAL.YEAR_START
        year_end = config.GENERAL.YEAR_END

        experiment = get_experiment_paths(config, data_dir)
        rx5_sparta_file = experiment.rx5_file
        event_5day_totals = experiment.event_file
        arealogpath = experiment.arealogpath
        varname = experiment.varname
        outpath = experiment.outpath

        outpath.mkdir(parents=True, exist_ok=True)
        Path(outpath, "suppl").mkdir(parents=True, exist_ok=True)

        rx5_sparta = xr.open_dataarray(rx5_sparta_file)
        histmax = rx5_sparta.sel(time=slice(str(year_start), str(year_end - 1))).max(
            dim="time"
        )
        histmax = histmax.rio.write_crs(epsg)
        # rx5_2024 = rx5_sparta.sel(time=f"{year_end}-01-01")
        rx5_2024 = xr.open_dataset(event_5day_totals)[varname]
        rx5_2024 = rx5_2024.rio.write_crs(epsg)

        if arealogpath.exists():
            arealogpath.unlink()
        else:
            arealogpath.touch()

        percentage_vs_histmax = calc_percentage_change(rx5_2024, histmax)
        plt_composite_maps(
            xda_rx5day_2024=rx5_2024,
            percentage_2024_vs_clim=percentage_vs_histmax,
            savefile=f"{outpath}/fig1.png",
            titlestr_1="Event total precipitation (12–16 September 2024)",
            titlestr_2="Deviation for event total precipitation in 2024 from historic Rx5day (1961–2023)",
            clabel_1="Total precipitation [mm]",
        )

        ## check area % increases for major summer floods: 1997, 2002, 2005, 2013
        major_flood_years = [1997, 2002, 2005, 2013]
        for year_iter in major_flood_years:
            past_histmax = rx5_sparta.sel(
                time=slice(str(year_start), str(year_iter - 1))
            ).max(dim="time")
            rx5_flood = rx5_sparta.sel(time=str(year_iter))
            percentage_flood = calc_percentage_change(rx5_flood, past_histmax)
            plt_composite_maps(
                xda_rx5day_2024=rx5_flood,
                percentage_2024_vs_clim=percentage_flood,
                titlestr_1=f"Rx5day {year_iter}",
                titlestr_2=f"Deviation for Rx5day in {year_iter} from historic Rx5day (1961–{year_iter - 1})",
                savefile=f"{outpath}/suppl/fig_suppl_flood_{year_iter}.png",
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
        exceedances_list = []
        for stationname, content in rls.items():
            dfrl_iter = pd.DataFrame(content["rls"])
            dfrl_list.append(dfrl_iter)
            dfmo_iter = pd.DataFrame(content["modeled_obs"])
            mod_obs_list.append(dfmo_iter)
            dfeo_iter = pd.DataFrame(content["empirical_obs"])
            dfeo_iter["station"] = stationname
            dfexceedances_iter = pd.DataFrame(content["empirical_obs_exc"])
            dfexceedances_iter["station"] = stationname
            emp_obs_list.append(dfeo_iter)
            exceedances_list.append(dfexceedances_iter)
        dfrl = pd.concat(dfrl_list, ignore_index=True)
        dfmo = pd.concat(mod_obs_list, ignore_index=True)
        dfeo = pd.concat(emp_obs_list, ignore_index=True)
        dfexceedances = pd.concat(exceedances_list, ignore_index=True)
        dfrl.to_csv(str(Path(data_dir, "rls.csv")), index=False)
        dfmo.to_csv(str(Path(data_dir, "modeled_obs.csv")), index=False)
        dfeo.to_csv(str(Path(data_dir, "empirical_obs.csv")), index=False)
        dfexceedances.to_csv(str(Path(data_dir, "empirical_obs_exc.csv")), index=False)

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
                f", {dfmo.query(f'station == "{station}"')['rp_upper_ci95'].max():1.0f})"
            )
        print("#" * 30)
        station_plots = [
            "St. Pölten-Landhaus_5609",
            "Langenlebarn_4081",
            "Reichenau an der Rax_10511",
        ]

        plot_timeseries(rx5day_year, dfexceedances, dfrl, dfmo, cols=station_plots)

    if config.PLOT.COMPOSITE_V2:
        synop_date = config.SYNOPTIC.DATE
        synop_extent = list(config.SYNOPTIC.EXTENT)
        xda_z500 = load_era5_field(
            config.PATHS.ERA5.FILE_Z500, "z", synop_date, synop_extent
        )
        xda_tcwv = load_era5_field(
            config.PATHS.ERA5.FILE_TCWV, "tcwv", synop_date, synop_extent
        )
        synop_kwargs = {
            "xda_z500": xda_z500,
            "xda_tcwv": xda_tcwv,
            "extent": synop_extent,
            "date_label": synop_date,
            "titlestr": (
                "500 hPa geopotential height [gpm] and total column water vapour [kg m$^{-2}$]"
            ),
        }

        Path("doc").mkdir(parents=True, exist_ok=True)
        # standalone synoptic overview
        plt_synoptic_map(**synop_kwargs, savefile="doc/fig1-synop.png")

        # composite as baseline, with the synoptic overview as first panel
        rx5_2024_v2, percentage_vs_histmax_v2 = load_composite_fields(
            config, data_dir, epsg
        )
        logpath_v2 = Path("doc", "area_affected_fig1-v2.log")
        if logpath_v2.exists():
            logpath_v2.unlink()
        else:
            logpath_v2.touch()
        plt_composite_maps(
            xda_rx5day_2024=rx5_2024_v2,
            percentage_2024_vs_clim=percentage_vs_histmax_v2,
            savefile="doc/fig1-v2.png",
            titlestr_1="Event total precipitation (12–16 September 2024)",
            titlestr_2="Deviation for event total precipitation in 2024 from historic Rx5day (1961–2023)",
            clabel_1="Total precipitation [mm]",
            synoptic=synop_kwargs,
            logpath=logpath_v2,
        )

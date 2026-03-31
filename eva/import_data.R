#-------------------------------------------------------------------------------
# Import and preprocess station data
#
# hsc, 02.2026
#-------------------------------------------------------------------------------

suppressPackageStartupMessages(
  require("tidyverse")
)

# NA-value
missval <- 9999

# daily moving window 5day sums
d5x <- read_csv("dat/station_data_pivot_rx5day.csv", show_col_types = FALSE) |>
  mutate(across(!any_of(1), ~ na_if(., missval)))

# block maxima
bm5x <- read_csv(
  "dat/station_data_pivot_rx5day_year.csv",
  show_col_types = FALSE
) |>
  mutate(across(!any_of(1), ~ na_if(., missval)))

abs_max <- map(.x = names(d5x)[-1], .f = function(n) {
  data.frame(Station = n, max_date = d5x$date, max = d5x[, n] |> pull()) |>
    na.omit() |>
    group_by(year(max_date)) |>
    slice_max(max) |>
    ungroup() |>
    dplyr::select(Station, max, max_date) |>
    arrange(desc(max)) |>
    head(1)
}) |>
  bind_rows()

meta <- map(.x = names(bm5x)[-1], .f = function(n) {
  x <- tibble(date = bm5x$date, val = bm5x[[n]]) |>
    na.omit()
  parts <- str_split(n, "_") |>
    unlist()
  tibble(
    id = parts[2],
    Station = n,
    years = length(unique(year(x$date))),
    min = min(x$val),
    mean = mean(x$val)
  )
}) |>
  bind_rows() |>
  left_join(abs_max, by = "Station")

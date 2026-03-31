#-------------------------------------------------------------------------------
# Bayesian EVA for September 2024 rainfall event in Austria
#
# hsc, 02.2026
#-------------------------------------------------------------------------------

library("tidyverse")
library("extRemes")
library("glue")
library("rstan")
library("knitr")
library("exdex")
library("cowplot")
library("loo")

#-------------------------------------------------------------------------------
# load data ----
#-------------------------------------------------------------------------------

source("eva/import_data.R")
source("eva/utils.R")

#------------------------------------------------------------------------------
# test asymptotic dependence ----
#------------------------------------------------------------------------------
# if stations are asymptotically dependent,
# it makes sense to pool the shape parameter
long_stations <- meta |>
  filter(years > 50) |>
  pull(Station)

# Loop through pairs and print the Chi value at a high threshold
pairs <- combn(long_stations, 2, simplify = FALSE)
dep_test <- map(pairs, ~ taildep(d5x[, .x], u = 0.99, na.rm = TRUE)) |>
  bind_rows()

knitr::kable(
  dep_test,
  caption = "Bivariate tail dependence across the four longest dataseries at the 0.99 quantile."
)
# chi is way above zero at the asymptotic limit, suggesting tail dependence.
# chi-bar however tells us that at the extreme limits the tails become independent.
# this can be expected for alpine regions because for the real large events
# also orography plays a crucial role.

#-------------------------------------------------------------------------------
# threshold and runs evaluation ----
#-------------------------------------------------------------------------------
all_exceedances <- numeric()
site_indices <- integer()
thresholds_used <- numeric(nrow(meta)) # To keep track for return level calcs
lambda_rates <- numeric(nrow(meta)) # Rate of events per year
station_names <- names(d5x)[-1] # Exclude the date column

# manual threshold selection
# Cooley, 2007:
# extRemes::mrlplot: should behave linearly for GPD data
# extRemes::threshrange.plot: should be constant as the threshold varies for GPD
i <- 10
series <- d5x[[station_names[i]]]
series <- series[!is.na(series)]
r <- quantile(series, c(0.8, 0.995))
quantile(series, c(0.8, 0.9, 0.95, .99, .995))
mrlplot(series)
threshrange.plot(series, r, nint = 20)
thresholds_used[1] <- 78
thresholds_used[2] <- 58
thresholds_used[3] <- 94
thresholds_used[4] <- 90
thresholds_used[5] <- 80
thresholds_used[6] <- 78
thresholds_used[7] <- 52
thresholds_used[8] <- 70
thresholds_used[9] <- 88
thresholds_used[10] <- 95
tibble(
  station = station_names[1:10],
  man_thresh = thresholds_used[1:10]
) |>
  mutate(
    series = map(station, ~ d5x[[.x]] |> discard(is.na)),
    q_thresh = map_dbl(series, ~ quantile(.x, 0.985)),
    man_length = map2_int(series, man_thresh, ~ sum(.x > .y)),
    q_length = map2_int(series, q_thresh, ~ sum(.x > .y))
  ) |>
  select(-series)
# follwoing the above analysis, we use this threshold
q_thresh <- 0.985

# check extremal index to estimate reasonable run-lengths for declustering
# if theta is low, clusters are long
# $\theta = 1$ means events are perfectly independent, and $\theta \to 0$ means events are highly clustered.
# look for a theta plateau, the k value is then the optimal runs length
# this has to be done manually
k_values <- 1:15 # the runs length
map(.x = seq_along(station_names), .f = function(i) {
  s_name <- station_names[i]
  series <- d5x[[s_name]]
  # remove NAs for the specific station (important for the 12-year vs 120-year gap)
  series <- series[!is.na(series)]
  u <- quantile(series, q_thresh)
  # u <- thresholds_used[i]
  theta_estimates <- sapply(k_values, function(k) {
    res <- kgaps(series, u, k = k)
    res$theta
  })
  tibble(s_name = s_name, k = k_values, theta = theta_estimates)
}) |>
  bind_rows() |>
  ggplot(aes(k, theta)) +
  geom_line() +
  geom_point() +
  geom_vline(xintercept = 13, color = "red", linetype = "dashed") +
  facet_wrap(~s_name, nrow = 2)

# suggests a run length at around 13 days for all of the stations
run_length <- 13

# loop over all stations
for (i in seq_along(station_names)) {
  s_name <- station_names[i]
  series <- d5x[[s_name]]

  # Remove NAs for the specific station
  series <- series[!is.na(series)]

  # 1. set threshold
  u <- quantile(series, q_thresh)
  thresholds_used[i] <- u

  # 2. decluster
  dc <- decluster(series, threshold = u, r = run_length)

  # 3. extract only the cluster peaks (Independent events)
  peaks <- as.vector(dc[dc > u & !is.na(dc)])

  # 4. store (value - threshold)
  excs <- peaks - u
  all_exceedances <- c(all_exceedances, excs)
  site_indices <- c(site_indices, rep(i, length(excs)))

  # 5. calculate event rate per year (needed for return levels later)
  # Roughly: total peaks / total years of record
  years_record <- length(series) / 365.25
  lambda_rates[i] <- length(peaks) / years_record
}

#-------------------------------------------------------------------------------
# fitting a Bayesian GPD model with shape parameter pooling ----
#-------------------------------------------------------------------------------

# final format for Stan
stan_data <- list(
  N = length(all_exceedances),
  S = length(station_names),
  y = all_exceedances,
  site = site_indices
)

# fitting
fit <- stan(
  file = "eva/gpd_pooled.stan",
  data = stan_data,
  iter = 4000,
  chains = 4,
  cores = parallel::detectCores(),
  control = list(adapt_delta = 0.99)
)

# basic diagnostics
plot(fit, pars = "xi")
print(fit, pars = c("xi", "sigma"))

#-------------------------------------------------------------------------------
# validation ----
#-------------------------------------------------------------------------------
# To see if pooling the shape parameter was actually a good idea,
# we use Leave-One-Out Cross-Validation (LOO-CV).
# We compare the pooled model with an unpooled model,
# where the shape parameter can vary across the region

init_fun <- function() {
  list(
    sigma = rep(20, 10), # start with a plausible scale
    xi = rep(0.1, 10) # start with a safe, positive shape
  )
}

fit_unpooled <- stan(
  file = "eva/gpd_unpooled.stan",
  data = stan_data,
  iter = 4000,
  init = init_fun,
  chains = 4,
  cores = parallel::detectCores(),
  control = list(
    adapt_delta = 0.99,
    max_treedepth = 15
  )
)

plot(fit_unpooled, pars = "xi")
print(fit_unpooled, pars = c("xi", "sigma"))

# extract log-likelihood from the pooled model
log_lik_pooled <- extract_log_lik(fit, parameter_name = "log_lik")
loo_pooled <- loo(log_lik_pooled)

# extract log-likelihood from the unpooled model
log_lik_unpooled <- extract_log_lik(fit_unpooled)
loo_unpooled <- loo(log_lik_unpooled)

# Compare
comp <- loo_compare(loo_pooled, loo_unpooled)
print(comp)

# check
plot(loo_pooled, main = "Pareto k Diagnostics: Pooled Model")
plot(loo_unpooled, main = "Pareto k Diagnostics: Unpooled Model")

return_periods <- c(2, 5, 10, 20, 50, 100, 200)

# extract posterior samples
params <- extract(fit)

plot_data <- expand_grid(i = 1:10, ReturnPeriod = return_periods) |>
  rowwise() |>
  mutate(
    Station = station_names[i],
    u = thresholds_used[i],
    lam = lambda_rates[i],
    rl_samps = list(u + (params$sigma[, i] / params$xi) * ((ReturnPeriod * lam)^params$xi - 1))
  ) |>
  summarise(
    Station, ReturnPeriod,
    Median = median(rl_samps),
    Lower = quantile(rl_samps, 0.025),
    Upper = quantile(rl_samps, 0.975),
    .groups = "drop"
  )

ggplot(
  plot_data,
  aes(x = ReturnPeriod, y = Median, color = Station, fill = Station)
) +
  geom_line(linewidth = 1) +
  geom_ribbon(aes(ymin = Lower, ymax = Upper), alpha = 0.1, color = NA) +
  scale_x_log10(breaks = return_periods) +
  labs(
    title = "Regional Bayesian EVA: 5-Day Precipitation Sums",
    subtitle = glue(
      "Pooled Shape (xi ~ {round(mean(params$xi),4)}), Individual Scale (sigma)"
    ),
    x = "Return Period (Years, Log Scale)",
    y = "5-Day Rain Sum (mm)"
  ) +
  theme(legend.position = "bottom")

params <- extract(fit)

# Example for the 12-year record (say it's station 5)
rl_12yr_station <- calc_rl(5, 100)

# Summary of 100-year return levels
summary_table <- tibble(
  Station = station_names[1:10],
  Threshold_u = thresholds_used[1:10],
  lambda = lambda_rates[1:10],
  idx = 1:10
) |>
  mutate(
    rl100_samples = pmap(
      .l = list(idx, Threshold_u, lambda),
      .f = function(i, u, lam) {
        u + (params$sigma[, i] / params$xi) * ((100 * lam)^params$xi - 1)
      }
    ),
    Median_100yr = map_dbl(rl100_samples, median),
    Lower_95 = map_dbl(rl100_samples, \(x) quantile(x, 0.025)),
    Upper_95 = map_dbl(rl100_samples, \(x) quantile(x, 0.975)),
    Uncertainty_Ratio = Upper_95 / Median_100yr
  ) |>
  select(-idx, -rl100_samples)

#-------------------------------------------------------------------------------
# block maxima
#-------------------------------------------------------------------------------

block_maxima <- sapply(station_names, function(s) max(d5x[[s]], na.rm = TRUE))
max_period_analysis <- map2_dfr(seq_len(nrow(meta)), block_maxima, get_return_period) |>
  as_tibble() |>
  print()

# for all years
bm_list <- bm5x |>
  select(-1) |>
  map(~ sort(stats::na.omit(.x)))

max_period_analysis_list <- map2(
  .x = seq_along(bm_list), .y = bm_list,
  .f = ~ map(.y, \(x) get_return_period(.x, x)) |> list_rbind()
)

#-------------------------------------------------------------------------------
# results ----
#-------------------------------------------------------------------------------

# 1. Generate the Growth Curves (Model Predictions)
# We'll reuse the 'plot_data' from our previous step or regenerate it here
# for a smooth range of return periods (e.g., 2 to 500 years)
rp_range <- exp(seq(log(2), log(2000), length.out = 100))

curves <- tibble(
  idx = seq_along(station_names),
  Station = station_names,
  u = thresholds_used,
  lam = lambda_rates
) |>
  crossing(ReturnPeriod = rp_range) |>
  mutate(
    Median = pmap_dbl(
      .l = list(idx, u, lam, ReturnPeriod),
      .f = function(i, u, lam, T) {
        rl_samples <- get_rl_from_params(u = u, lam = lam, T = T, params = params, i = i)
        median(rl_samples)
      }
    )
  ) |>
  select(Station, ReturnPeriod, Median)

# 2. Add the Observed Block Maxima
# 'max_period_analysis' contains the median T and Input_Value for each station
obs_points <- max_period_analysis

# 3. Final Visualization
ggplot() +
  # Draw the station-specific growth curves
  geom_line(
    data = curves,
    aes(x = ReturnPeriod, y = Median, color = Station),
    alpha = 0.6,
    linewidth = 0.8
  ) +
  # Plot the Block Maxima
  geom_point(
    data = obs_points,
    aes(x = Median_T, y = Input_Value, color = Station),
    size = 4,
    shape = 18
  ) +
  # Add horizontal/vertical error bars for the Block Maxima T uncertainty
  geom_errorbarh(
    data = obs_points,
    aes(y = Input_Value, xmin = Lower_CI, xmax = Upper_CI, color = Station),
    height = 0.2,
    alpha = 0.5
  ) +
  scale_x_log10(
    breaks = c(2, 5, 10, 20, 50, 100, 200, 500, 1000, 1200, 1500, 2000)
  ) +
  annotation_logticks(sides = "b") +
  labs(
    title = "Historical Maxima vs. Regional Bayesian Growth Curves",
    subtitle = "Diamonds represent observed block maxima with 95% uncertainty in Return Period",
    x = "Return Period (Years, Log Scale)",
    y = "5-Day Precipitation Sum (mm)"
  ) +
  theme(legend.position = "bottom")

# single station
rp_range <- exp(seq(log(2), log(2000), length.out = 100))

i <- 2
curves <- data.frame()
u <- thresholds_used[i]
lam <- lambda_rates[i]
for (T in rp_range) {
  rl_samples <- get_rl_from_params(u = u, lam = lam, T = T, params = params, i = i)
  curves <- rbind(
    curves,
    data.frame(
      Station = station_names[i],
      ReturnPeriod = T,
      Median = median(rl_samples)
    )
  )
}
obs_points <- max_period_analysis_list[[i]]

# observed yearly maxima
obs_points_emp <- data.frame(
  rl = sort(obs_points$Input_Value),
  rp = mevr::pp.weibull(obs_points$Input_Value)
)

ggplot() +
  # station-specific growth curves
  geom_line(
    data = curves,
    aes(x = ReturnPeriod, y = Median, color = Station),
    alpha = 0.6,
    linewidth = 0.8
  ) +
  # Block Maxima
  geom_point(
    data = obs_points,
    aes(x = Median_T, y = Input_Value, color = Station),
    size = 4,
    shape = 18
  ) +
  # empirical plotting position
  geom_point(
    data = obs_points_emp,
    aes(x = rp, y = rl),
    color = "black",
    size = 2,
    shape = 20
  ) +
  # error bars for the Block Maxima T uncertainty
  geom_errorbarh(
    data = obs_points,
    aes(y = Input_Value, xmin = Lower_CI, xmax = Upper_CI, color = Station),
    height = 0.2,
    alpha = 0.5
  ) +
  scale_x_log10(
    breaks = c(2, 5, 10, 20, 50, 100, 200, 500, 1000, 1200, 1500, 2000)
  ) +
  annotation_logticks(sides = "b") +
  labs(
    title = "Historical Maxima vs. Regional Bayesian Growth Curves",
    subtitle = "Diamonds represent observed block maxima with 95% uncertainty in Return Period",
    x = "Return Period (Years, Log Scale)",
    y = "5-Day Precipitation Sum (mm)"
  ) +
  theme(legend.position = "bottom")

#-------------------------------------------------------------------------------

# A "Dimensionless Growth Factor" plot is the gold standard in regional frequency analysis (RFA).
# It proves that while some stations are "wetter" than others (different $\sigma$),
# the relative increase of extremes (the "growth") follows the same physics.

# 1. Normalize the curves
# We calculate (RL - u) / sigma for the regional xi
rp_range <- exp(seq(log(1.1), log(2000), length.out = 100))
xi_median <- median(params$xi)

growth_curve <- data.frame(
  ReturnPeriod = rp_range,
  # The dimensionless GPD formula: ((T * lambda)^xi - 1) / xi
  GrowthFactor = ((rp_range * 1)^xi_median - 1) / xi_median
)

# 2. Normalize the observed block maxima
# Growth Factor = (Value - Threshold) / Sigma
obs_growth <- max_period_analysis |>
  mutate(
    Sigma_i = colMeans(params$sigma)[match(Station, station_names)],
    Obs_GrowthFactor = (Input_Value -
      thresholds_used[match(Station, station_names)]) /
      Sigma_i
  ) |>
  left_join(meta |> select(Station, max_date), by = "Station") |>
  mutate(label_text = paste0(Station, " (", max_date, ")"))

# 3. Plot
ggplot() +
  geom_line(
    data = growth_curve,
    aes(x = ReturnPeriod, y = GrowthFactor),
    color = "black",
    linewidth = 1.2
  ) +
  geom_point(
    data = obs_growth,
    aes(x = Median_T, y = Obs_GrowthFactor, color = Station),
    size = 4
  ) +
  scale_x_log10(breaks = c(2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000)) +
  labs(
    title = "Dimensionless Regional Growth Curve",
    subtitle = "All stations collapsed by their scale parameter sigma",
    x = "Return Period (Years)",
    y = "Dimensionless Growth Factor [(x-u)/sigma]"
  )


#-------------------------------------------------------------------------------
# Create a final summary table

report_table <- max_period_analysis |>
  left_join(
    summary_table |> select(Station, Median_100yr, Upper_95),
    by = "Station"
  ) |>
  right_join(meta, by = "Station") |>
  mutate(
    Max_Observed = round(Input_Value, 1),
    Return_Period_of_Max = round(Median_T, 0),
    RP_Lower = round(Lower_CI, 0),
    RP_Upper = round(Upper_CI, 0)
  ) |>
  select(
    Station,
    years,
    Max_Observed,
    max_date,
    Return_Period_of_Max,
    RP_Lower,
    RP_Upper,
    Median_100yr
  )

knitr::kable(
  report_table,
  col.names = c(
    "Station",
    "Years",
    "Max Obs (mm)",
    "Date Max Obs",
    "Est. RP (yrs)",
    "RP Low",
    "RP High",
    "100yr Design (mm)"
  )
)

#-------------------------------------------------------------------------------
# create results for paper ----
#-------------------------------------------------------------------------------
# For each year and station, the RP based on the respective Rx5day
# (maximum annual value) and the associated uncertainty range.

# Build per-station return-period summaries
rps <- imap(max_period_analysis_list, function(df, i) {
  n <- unique(df$Station)

  a <- df |>
    rename(max = Input_Value) |>
    as_tibble() |>
    arrange(max)

  b <- tibble(
    Station = n,
    max_date = d5x$date,
    max = d5x[[n]]
  ) |>
    filter(!is.na(max), max > thresholds_used[i]) |>
    group_by(yr = year(max_date)) |>
    slice_max(max, with_ties = FALSE) |>
    ungroup() |>
    select(Station, max, max_date) |>
    arrange(max)

  bind_cols(a[, 1:5], b[, "max_date"]) |>
    rename(
      station = Station,
      Rx5d = max,
      rp_lower_ci95 = Lower_CI,
      rp_median = Median_T,
      rp_upper_ci95 = Upper_CI,
      date_Rx5d = max_date
    ) |>
    select(station, Rx5d, date_Rx5d, rp_lower_ci95, rp_median, rp_upper_ci95)
}) |>
  set_names(bm5x[-1])

# Check each station has unique years
walk2(rps, names(rps), function(tbl, nm) {
  yrs <- tbl |>
    filter(station == nm) |>
    mutate(years = year(date_Rx5d)) |>
    pull(years) |>
    sort()

  dup_idx <- which(duplicated(yrs))
  if (length(dup_idx) > 0) {
    warning(sprintf(
      "Duplicated years in Station %s: years %s",
      nm, paste(unique(yrs[dup_idx]), collapse = ", ")
    ))
  }
})
rps <- set_names(rps, station_names)


write_rds(rps, file = "dat/rps.rds")

#-------------------------------------------------------------------------------

# return level plot (mm precip + uncertainty)
# single station
rp_range <- exp(seq(log(2), log(2000), length.out = 100))
alpha <- 0.05

rls <- imap(station_names, function(st, i) {
  u <- thresholds_used[i]
  lam <- lambda_rates[i]

  curves <- tibble(return_period = rp_range) |>
    mutate(
      samples = map(return_period, \(x) get_rl_from_params(u = u, lam = lam, T = x, params = params, i = i)),
      lower_ci = map_dbl(samples, \(x) quantile(x, alpha / 2)),
      median = map_dbl(samples, median),
      upper_ci = map_dbl(samples, \(x) quantile(x, 1 - alpha / 2))
    ) |>
    select(return_period, lower_ci, median, upper_ci) |>
    mutate(station = st, .before = 1)

  # Modeled return periods for observed block maxima (already computed)
  obs_points_mod <- rps[[st]]

  # Empirical return periods for observed maxima
  obs_points_emp <- tibble(
    rl_obs = sort(obs_points_mod$Rx5d),
    rp_obs = mevr::pp.weibull(obs_points_mod$Rx5d)
  )

  list(
    station = st,
    rls = curves,
    modeled_obs = obs_points_mod,
    empirical_obs = obs_points_emp
  )
}) |>
  set_names(station_names)
write_rds(rls, "dat/rls.rds")

#-------------------------------------------------------------------------------

# check plot
plot_rls_index <- function(rls, i, curve_cols = 3:5) {
  stopifnot(is.list(rls), i >= 1, i <= length(rls))
  stopifnot(all(c("rls", "modeled_obs", "empirical_obs") %in% names(rls[[i]])))
  curves <- rls[[i]]$rls |>
    pivot_longer(cols = {{ curve_cols }})
  obs_points_mod <- rls[[i]]$modeled_obs
  obs_points_emp <- rls[[i]]$empirical_obs
  ggplot() +
    geom_line(
      data = curves,
      aes(x = return_period, y = value, color = station, linetype = name),
      alpha = 0.6,
      size = 0.8
    ) +
    # modeled block maxima
    geom_point(
      data = obs_points_mod,
      aes(x = rp_median, y = Rx5d, color = station),
      size = 3,
      shape = 18
    ) +
    # empirical plotting position
    geom_point(
      data = obs_points_emp,
      aes(x = rp_obs, y = rl_obs),
      color = "black",
      size = 2,
      shape = 20
    ) +
    scale_linetype_manual(values = c("dashed", "solid", "dashed")) +
    scale_x_log10(
      breaks = c(2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000)
    ) +
    annotation_logticks(sides = "b") +
    labs(
      title = "Historical Maxima vs. Regional Bayesian return Levels",
      x = "Return Period (Years)",
      y = "5-Day Precipitation Return Level (mm)",
      linetype = ""
    ) +
    theme(legend.position = "bottom")
}

plot_rls_index(rls, i = 9)

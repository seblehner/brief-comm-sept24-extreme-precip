#-------------------------------------------------------------------------------
# Sensitivity analysis (run lengths, thresholds)
#
# hsc, 02.2026
#-------------------------------------------------------------------------------

library("tidyverse")
library("extRemes")
library("rstan")
library("cli")
library("glue")

#-------------------------------------------------------------------------------
# load data
#-------------------------------------------------------------------------------

source("eva/import_data.R")

#-------------------------------------------------------------------------------
# pepare data and fit models
#-------------------------------------------------------------------------------

thresholds <- c(0.95, 0.98, 0.985, 0.99, 0.995)
runlengths <- c(5, 8, 10, 13)
nn <- length(thresholds) * length(runlengths)
n <- 1
fits <- list()
for (q_thresh in thresholds) {
  for (run_length in runlengths) {
    cli_text(col_green(glue("Model {n}/{nn}")))
    cli_alert_info(glue(
      "Threshold: {col_blue(q_thresh)} Quantile, Runlength:  {col_blue(run_length)} days"
    ))

    all_exceedances <- numeric()
    site_indices <- integer()
    station_names <- names(d5x)[-1] # Exclude the date column

    cli_alert_info("\tData preparation")
    for (i in seq_along(station_names)) {
      s_name <- station_names[i]
      series <- d5x[[s_name]]

      # Remove NAs for the specific station (important for the 12-year vs 120-year gap)
      series <- series[!is.na(series)]

      # 1. Set a threshold
      u <- quantile(series, q_thresh)

      # 2. Decluster (Handling the 5-day moving window bias)
      # run.length = 5 ensures we don't double-count the same storm
      dc <- decluster(series, threshold = u, r = run_length)

      # 3. Extract only the cluster peaks (Independent events)
      peaks <- as.vector(dc[dc > u & !is.na(dc)])

      # 4. Store (Value - Threshold)
      excs <- peaks - u
      all_exceedances <- c(all_exceedances, excs)
      site_indices <- c(site_indices, rep(i, length(excs)))

      # 5. Calculate rate of events per year (needed for return levels later)
      # Roughly: total peaks / total years of record
      years_record <- length(series) / 365.25
      # lambda_rates[i] <- length(peaks) / years_record
    }

    #-------------------------------------------------------------------------------
    # fitting a bayesian GPD model with shape parameter pooling
    #-------------------------------------------------------------------------------
    cli_alert_info("\tFitting Stan model")
    stan_data <- list(
      N = length(all_exceedances),
      S = length(station_names),
      y = all_exceedances,
      site = site_indices
    )

    # fitting
    rm(fit)
    fit <- stan(
      file = "eva/gpd_pooled.stan",
      data = stan_data, # list containing N, S, y, and site
      iter = 10000,
      chains = 4,
      cores = parallel::detectCores(),
      control = list(adapt_delta = 0.99) # extra stability for the tail estimation
    )
    cli_alert_success("Successfully fitted Stan model")

    #-------------------------------------------------------------------------------
    # Basic Diagnostics
    # plot(fit, pars = "xi")
    # print(fit, pars = c("xi", "sigma"))
    params <- extract(fit)
    cli_alert_info("xi =  {mean(params$xi)}")
    fits[[as.character(glue("{q_thresh}-{run_length}"))]] <- summary(fit)
    n <- n + 1
  }
}

# types <- names(fits)
# res <- imap(fits, function(x, nme) {
#   summary(x)
# })
saveRDS(fits, "dat/sensitivity_analysis_fits.Rds")

# inspect
# params <- lapply(seq_along(res), function(i) {
params <- lapply(names(res), function(nme) {
  # x <- res[[i]][["summary"]]
  x <- res[[nme]][["summary"]]
  rn <- rownames(x)
  parts <- str_split(nme, "-") |>
    unlist()
  as_tibble(x) |>
    mutate(par = rn, thresh = parts[1], runlen = parts[2])
})
params <- do.call(rbind, params)

params |>
  filter(par == "xi") |>
  mutate(frunlen = factor(runlen, levels = c("5", "8", "10", "13"))) |>
  ggplot(aes(factor(thresh), mean, group = frunlen, color = frunlen)) +
  geom_line() +
  scale_y_continuous(limits = c(0, 0.5)) +
  labs(y = "mean xi", x = "threshold quantile", color = "runlength (days)")

params |>
  filter(par == "xi", thresh != "0.95") |>
  dplyr::select(mean, sd)

params |>
  filter(par == "xi") |>
  mutate(frunlen = factor(runlen, levels = c("5", "8", "10", "13"))) |>
  ggplot(aes(factor(thresh), sd, group = frunlen, color = frunlen)) +
  geom_line() +
  #  scale_y_continuous(limits = c(0, 0.5)) +
  labs(y = "sd xi", x = "threshold quantile", color = "runlength (days)")

params |>
  pivot_longer(cols = par) |>
  filter(value %in% paste0("sigma[", 1:10, "]")) |>
  mutate(frunlen = factor(runlen, levels = c("5", "8", "10", "13"))) |>
  ggplot(aes(factor(thresh), mean, group = frunlen, color = frunlen)) +
  geom_line() +
  labs(y = "mean sigma", x = "threshold quantile", color = "runlength (days)") +
  facet_wrap(. ~ value)

params |>
  pivot_longer(cols = par) |>
  filter(value %in% paste0("sigma[", 1:10, "]")) |>
  mutate(frunlen = factor(runlen, levels = c("5", "8", "10", "13"))) |>
  ggplot(aes(factor(thresh), sd, group = frunlen, color = frunlen)) +
  geom_line() +
  labs(y = "sd sigma", x = "threshold quantile", color = "runlength (days)") +
  facet_wrap(. ~ value)

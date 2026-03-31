#-------------------------------------------------------------------------------
# Baysian Hierarchical GEV Model with poooled shape
#
# hsc, 02.2026
#-------------------------------------------------------------------------------

library("tidyverse")
library("extRemes")
library("glue")
library("rstan")

#-------------------------------------------------------------------------------
# load data
#-------------------------------------------------------------------------------

source("eva/import_data.R")

#-------------------------------------------------------------------------------
# fit gev
#-------------------------------------------------------------------------------

df_long <- data.frame(
  precip = as.vector(as.matrix(bm5x[, -1])),
  s_id = rep(1:nrow(meta), each = nrow(bm5x))
) |>
  na.omit()

stan_data_gev <- list(
  N_obs = nrow(df_long),
  N_stations = nrow(meta),
  y = df_long$precip,
  station_idx = df_long$s_id
)

fit_gev <- stan(
  file = "eva/bayes_gev/gev_pooled.stan",
  data = stan_data_gev,
  iter = 4000,
  chains = 4,
  cores = 4,
  control = list(adapt_delta = 0.99) # Extra stability for the tail estimation
)

plot(fit_gev, pars = "xi")
print(fit_gev, pars = c("xi", "sigma"))

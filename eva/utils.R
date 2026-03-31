# get return levels
get_rl <- function(u, lam, T, sigma, xi) {
  u + (sigma / xi) * ((T * lam)^xi - 1)
}

# Convenience wrapper when using `params` and station index `i`
get_rl_from_params <- function(u, lam, T, params, i) {
  get_rl(u = u, lam = lam, T = T, sigma = params$sigma[, i], xi = params$xi)
}

# Calculate RL for site 'i'
calc_rl <- function(site_idx, T_years = 100) {
  sigma_samples <- params$sigma[, site_idx]
  xi_samples <- params$xi
  u <- thresholds_used[site_idx]
  lam <- lambda_rates[site_idx]

  rl_samples <- get_rl(u = u, lam = lam, T = T_years, sigma = sigma_samples, xi = xi_samples)

  tibble(
    mean = mean(rl_samples),
    low = quantile(rl_samples, 0.025),
    high = quantile(rl_samples, 0.975)
  )
}


#' Estimate Return Period for a specific value
#' @param station_idx Integer, 1 to 10
#' @param value The precipitation sum (e.g., the block maximum of the series)
#' @param alpha The significance level for the credible interval (default 0.05 for 95% CI)
get_return_period <- function(station_idx, value, alpha = 0.05) {
  # 1. Extract parameters
  sigmas <- params$sigma[, station_idx]
  xis <- params$xi
  u <- thresholds_used[station_idx]
  lam <- lambda_rates[station_idx]

  # 2. Check if the value is below the threshold
  if (value <= u) {
    warning("Value must be above the threshold used in the model (u).")
    return()
  }

  # 3. Calculate Return Period (T) for every MCMC sample
  # Formula: T = (1/lambda) * (1 + xi * (x-u)/sigma)^(1/xi)
  # We use the 'pmax' to ensure the term inside the exponent is positive
  excess <- value - u
  term <- 1 + (xis * excess) / sigmas

  # If term <= 0, the value is theoretically impossible for that xi/sigma combo
  # We handle this by setting those to Inf
  t_samples <- ifelse(term > 0, (1 / lam) * (term^(1 / xis)), Inf)

  # 4. Calculate Quantiles for Uncertainty
  probs <- c(alpha / 2, 0.5, 1 - alpha / 2)
  res <- quantile(t_samples, probs = probs, na.rm = TRUE)

  return(data.frame(
    Station = station_names[station_idx],
    Input_Value = value,
    Lower_CI = res[1],
    Median_T = res[2],
    Upper_CI = res[3],
    Prob_Exceedance_Annual = 1 / res[2]
  ))
}

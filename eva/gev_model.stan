data {
  int<lower=0> N;          // Number of observations
  vector[N] y;             // Declustered maxima
}

parameters {
  real mu;                 // Location parameter
  real<lower=0> sigma;     // Scale parameter
  real xi;                 // Shape parameter
}

model {
  // Likelihood: GEV distribution
  for (n in 1:N) {
    if (xi != 0) {
      target += gev_lpdf(y[n] | mu, sigma, xi);
    } else {
      target += gumbel_lpdf(y[n] | mu, sigma);
    }
  }
  // Weakly informative priors
  mu ~ normal(0, 10);
  sigma ~ normal(0, 10);
  xi ~ normal(0, 2);
}

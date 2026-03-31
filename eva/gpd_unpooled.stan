// Generalized Pareto Distribution - Pooled Shape Parameter
// Designed for multiple stations with varying record lengths.
// All stations share 'xi', but each has its own 'sigma'.

data {
  int<lower=0> N;                  // Total number of independent exceedances
  int<lower=1> S;                  // Total number of stations (e.g., 10)
  vector[N] y;                     // Exceedance values (Peak - Threshold)
  int<lower=1, upper=S> site[N];    // Mapping of each exceedance to its station ID
}

parameters {
  vector<lower=0>[S] sigma;        // Scale parameter for each station
  //real<lower=-0.5, upper=0.5> xi;  // Shared shape parameter (constrained for hydrology)
  vector<lower=-0.5, upper=0.5>[S] xi; // shape parameter per station
}

model {
  // --- Priors ---
  // Weakly informative: Allows data to dominate while preventing physical impossibilities
  sigma ~ normal(0, 100); 
  xi ~ normal(0, 0.2); 
  
  // --- Likelihood ---
  for (n in 1:N) {
    // We use the 'target += ' syntax to define the log-posterior
    if (abs(xi[site[n]]) < 1e-9) { 
      // Limit as xi approaches 0 (Exponential Distribution)
      target += -y[n] / sigma[site[n]] - log(sigma[site[n]]);
    } else {
      // Standard GPD log-likelihood
      // log1p(x) is more numerically stable than log(1 + x)
      target += -(1/xi[site[n]] + 1) * log1p(xi[site[n]] * y[n] / sigma[site[n]]) - log(sigma[site[n]]);
    }
  }
}

generated quantities {
  vector[N] log_lik;
  for (n in 1:N) {
    if (abs(xi[site[n]]) < 1e-9) {
      log_lik[n] = -y[n] / sigma[site[n]] - log(sigma[site[n]]);
    } else {
      log_lik[n] = -(1/xi[site[n]] + 1) * log1p(xi[site[n]] * y[n] / sigma[site[n]]) - log(sigma[site[n]]);
    }
  }
}

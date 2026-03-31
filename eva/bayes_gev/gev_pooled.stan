functions {
  // GEV log-density function
  real gev_lpdf(real y, real mu, real sigma, real xi) {
    real z = (y - mu) / sigma;
    if (abs(xi) < 1e-15) { // Handle the Gumbel case (limit as xi -> 0)
      return -log(sigma) - z - exp(-z);
    } else {
      real v = 1 + xi * z;
      if (v <= 0) return negative_infinity(); // Ensure data is within support
      return -log(sigma) - (1 + 1/xi) * log(v) - pow(v, -1/xi);
    }
  }
}

data {
  int<lower=0> N_obs;              // Total number of observations across all stations
  int<lower=0> N_stations;         // 10
  vector[N_obs] y;                 // All annual maxima in one vector
  int<lower=1,upper=N_stations> station_idx[N_obs]; // Which station each y belongs to
}

parameters {
  real xi;                       
  vector[N_stations] mu;         
  vector<lower=0>[N_stations] sigma; 
}

model {
  // Priors: Broad enough to let data speak, tight enough to help convergence
  xi ~ normal(0.1, 0.3);         
  mu ~ normal(30, 30);           
  sigma ~ normal(20, 20);

  // Likelihood
  for (n in 1:N_obs) {
    target += gev_lpdf(y[n] | mu[station_idx[n]], sigma[station_idx[n]], xi);
  }
}

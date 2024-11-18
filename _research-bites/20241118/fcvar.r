# Load necessary libraries
if (!require("FCVAR")) {
    install.packages("FCVAR", repos = "http://cran.us.r-project.org")
}
if (!require("dplyr")) {
    install.packages("dplyr", repos = "http://cran.us.r-project.org")
}
library(FCVAR)
library(dplyr)

# Load the CSV file into a dataframe
df_merged <- read.csv("/Users/amyoumaymakhaldoun/Desktop/Panoptic Scripts/options_data/df_merged.csv")

# Ensure the timestamp column is converted to DateTime format if needed
df_merged$timestamp <- as.POSIXct(df_merged$timestamp, format="%Y-%m-%d %H:%M:%S")

# Prepare the data by selecting relevant columns and removing missing values
df_fcvar <- df_merged %>%
  select(iv_uniswap, iv_dvol) %>%
  na.omit()

# Define the parameters for the FCVAR model
rank <- 1       # Set cointegration rank
k <- 2          # Set number of lags

# Set up options for the FCVAR model estimation with the restrict option
opt <- FCVARoptions(
  gridSearch = TRUE,        # Enable grid search for parameter optimization
  dbMin = c(0.01, 0.01),    # Set lower bounds for d and b
  dbMax = c(2.00, 2.00),    # Set upper bounds for d and b
  model = 1,                # 1 for a constant model, 2 for a trend model
  trace = FALSE,            # Disable verbose output
  restrict = 1              # Enforce d = b
)

# Run the FCVAR model estimation
fcvar_result <- FCVARestn(df_fcvar, k = k, r = rank, opt = opt)

# Display a summary of the FCVAR model
print(summary(fcvar_result))

# Extract and print estimated parameters
estimated_d <- fcvar_result$d
estimated_bd <- fcvar_result$bd
cat("Estimated long memory parameter (d):", estimated_d, "\n")
cat("Estimated fractional cointegration order (b):", estimated_bd, "\n")

# Check if fractional cointegration exists
if (estimated_d > 0 && estimated_bd > 0 && estimated_d >= estimated_bd) {
  cat("The series are fractionally cointegrated.\n")
  cat("This implies that the two series share a long-term equilibrium relationship with persistent, slow-decaying adjustments to equilibrium.\n")
} else {
  cat("The series are not fractionally cointegrated.\n")
  cat("This implies that the series do not share a long-term equilibrium relationship with fractional integration.\n")
}

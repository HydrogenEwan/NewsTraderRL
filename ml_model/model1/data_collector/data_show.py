import numpy as np

# Load the .npy file
data = np.load("src/data/SP500/stocks_data.npy")

# Show basic info
print("Shape:", data.shape)
print("Dtype:", data.dtype)

# Show first few entries (5 by default)
print("First few entries:\n", data[:5])

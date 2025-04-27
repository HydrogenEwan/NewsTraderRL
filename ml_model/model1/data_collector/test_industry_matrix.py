#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to generate and display an industry classification matrix for 10 selected companies.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from .data_collection import create_multi_industry_classification

# Select 10 companies from DJIA
selected_companies = [
    'AAPL',  # Apple Inc. - Technology
    'JPM',   # JPMorgan Chase & Co. - Financial Services
    'JNJ',   # Johnson & Johnson - Healthcare
    'PG',    # Procter & Gamble - Consumer Goods
    'WMT',   # Walmart Inc. - Retail
    'DIS',   # Walt Disney Company - Entertainment
    'MSFT',  # Microsoft Corporation - Technology
    'V',     # Visa Inc. - Financial Services
    'HD',    # Home Depot Inc. - Retail
    'KO'     # Coca-Cola Company - Beverages
]

# Get company names and industries
print("Fetching company information...")
company_info = {}
for symbol in selected_companies:
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        company_name = info.get('longName', symbol)
        industry = info.get('industry', 'Unknown')
        sector = info.get('sector', 'Unknown')
        company_info[symbol] = {
            'name': company_name,
            'industry': industry,
            'sector': sector
        }
        print(f"{symbol}: {company_name} - Industry: {industry}, Sector: {sector}")
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        company_info[symbol] = {
            'name': symbol,
            'industry': 'Unknown',
            'sector': 'Unknown'
        }

# Download stock data for the selected companies
print("\nDownloading stock data for selected companies...")
stock_data_list = []
for symbol in selected_companies:
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1y")
        stock_data_list.append(data)
        print(f"Downloaded data for {symbol}")
    except Exception as e:
        print(f"Error downloading data for {symbol}: {e}")
        stock_data_list.append(None)

# Create the industry classification matrix
print("\nCreating industry classification matrix...")
industry_matrix = create_multi_industry_classification(len(selected_companies), selected_companies, stock_data_list)

# Create a DataFrame for better visualization
df = pd.DataFrame(industry_matrix, index=selected_companies, columns=selected_companies)

# Display the matrix
print("\nIndustry Classification Matrix:")
print(df.round(3))

# Visualize the matrix
plt.figure(figsize=(12, 10))
sns.heatmap(df, annot=True, cmap='YlGnBu', fmt='.3f', linewidths=.5)
plt.title('Industry Classification Matrix')
plt.tight_layout()
plt.savefig('industry_matrix_heatmap.png')
print("\nHeatmap saved as 'industry_matrix_heatmap.png'")

# Analyze the matrix
print("\nMatrix Analysis:")
print(f"Average relationship strength: {np.mean(industry_matrix):.3f}")
print(f"Maximum relationship strength: {np.max(industry_matrix):.3f}")
print(f"Minimum relationship strength: {np.min(industry_matrix):.3f}")

# Find strongest relationships
print("\nStrongest relationships:")
for i in range(len(selected_companies)):
    for j in range(i+1, len(selected_companies)):
        if industry_matrix[i, j] > 0.5:
            print(f"{company_info[selected_companies[i]]['name']} - {company_info[selected_companies[j]]['name']}: {industry_matrix[i, j]:.3f}")

# Group companies by similarity
print("\nCompany groups by similarity:")
threshold = 0.5
groups = []
used = set()

for i in range(len(selected_companies)):
    if i in used:
        continue
    
    group = [selected_companies[i]]
    used.add(i)
    
    for j in range(i+1, len(selected_companies)):
        if j not in used and industry_matrix[i, j] > threshold:
            group.append(selected_companies[j])
            used.add(j)
    
    if len(group) > 1:
        groups.append(group)

for i, group in enumerate(groups):
    group_names = [company_info[symbol]['name'] for symbol in group]
    print(f"Group {i+1}: {', '.join(group_names)}") 
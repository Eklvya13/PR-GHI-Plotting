import argparse
from datetime import datetime
import pandas as pd
import numpy as np
import os, math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    parser = argparse.ArgumentParser(description="Generate PR graph for a given date range.")
    parser.add_argument("--start_date", type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", type=str, help="End date in YYYY-MM-DD format")
    args = parser.parse_args()

    startDate = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    endDate = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None

    # Make sure that the GHI & PR folder are present in the Data folder which is in the same directory as main.py file
    preprocessing()

    #Plot will be displayed as well saved as jpeg in the plotImg folder
    plotter(startDate, endDate)

def preprocessing():
    # walker function that traverses file structure
    def csvWalker(dir):
        csvData = []
        for root, subDir, files in os.walk(dir):
            for file in files:
                # adds content of csv to a dataframe
                if file.endswith('.csv'):
                    csvPath = os.path.join(root, file)
                    tempDf = pd.read_csv(csvPath)
                    tempDf['Date'] = pd.to_datetime(tempDf['Date'])
                    csvData.append(tempDf)
        return pd.concat(csvData)

    dataDir = './data'
    ghiDir = os.path.join(dataDir, 'GHI')
    prDir = os.path.join(dataDir, 'PR')

    ghiCsvData = csvWalker(ghiDir)
    prCsvData = csvWalker(prDir)

    combinedData = pd.merge(ghiCsvData, prCsvData, on = 'Date', how = 'inner')
    
    # sorting to make sure that the orders are correct 
    combinedData = combinedData.sort_values('Date')

    #saving as csv    
    combinedData.to_csv('combined.csv', index= False)



def plotter(startDate=None, endDate=None):
    # this function fetches data from a csv within the given date range
    def fetchCsvData(startDate=None, endDate=None, filePath='combined.csv'):
        csvData = pd.read_csv(filePath)
        csvData['Date'] = pd.to_datetime(csvData['Date'])
        if startDate is not None and endDate is not None:
            filteredData = csvData[(csvData['Date'] >= startDate) & 
                                (csvData['Date'] <= endDate)]
        else:
            return csvData.sort_values('Date')
        return filteredData.sort_values('Date')

    # Yearly Budget calculation logic >> decrement of 0.8% per year         
    def budgetValues(csvData, startDate):
        initialBudget = 73.9
        reduceRate = 0.008
        budget = []
        for date in csvData['Date']:
            year = math.floor((date.year - startDate.year) + (date.month - startDate.month) // 12)
            cur = initialBudget * (1 - reduceRate) ** year
            budget.append(cur)
        return budget
    

    startDate = pd.to_datetime(startDate)
    endDate = pd.to_datetime(endDate)
    csvData = fetchCsvData(startDate, endDate) 

    # This Handles if there is no data for the given Date Range or Incorrect Date Range
    if len(csvData) == 0:
        print("No Data for the given Date Range!")
        return

    # Here I give Default Values if argumensts are not present 
    if not startDate and not endDate:
        startDate = csvData['Date'][0]
        endDate = csvData['Date'].iloc[-1]

    # 30 Day Rolling Average
    csvData['PR_30avg'] = csvData['PR'].rolling(window=30).mean()

    # Yearly Budget
    csvData['Budget'] = budgetValues(csvData, startDate)

    colors = pd.cut(csvData['GHI'], bins=[-np.inf, 2, 4, 6, np.inf], labels=['navy', 'lightblue', 'orange', 'brown'])
    plt.figure(figsize=(14, 8))
    plt.grid(True)
    plt.margins(x=0)

    # Scatter plot for PR values
    plt.scatter(csvData['Date'], csvData['PR'], c=colors, s=10, label='PR values', marker='D')
   
    # Line plot for the Target Budget Yield Performance Ratio
    bgt = plt.plot(csvData['Date'], csvData['Budget'], color='green', linewidth=2, label='Target Budget Yield Performance Ratio [1Y-73.9%,2Y-73.3%,3Y-72.7%]')


    pointsAboveBudget = (csvData['PR'] > csvData['Budget']).sum()
    totalPoints = len(csvData)
    percTotalPoints = (pointsAboveBudget / totalPoints) * 100 # percentage - %
    
    # Line plot for the 30-day moving average of PR
    avg = plt.plot(csvData['Date'], csvData['PR_30avg'], color='red', linewidth=2, label=f'30-day moving average of PR\nPoints above Target Budget PR = {pointsAboveBudget}/{totalPoints} = {percTotalPoints:.2f}%')

    handles = [
    plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='navy', markersize=8, label='< 2'),
    plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='lightblue', markersize=8, label='2 - 4'),
    plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='orange', markersize=8, label='4 - 6'),
    plt.Line2D([0], [0], marker='D', color='w', markerfacecolor='brown', markersize=8, label='> 6')
    ]

    scatterLegend = plt.legend(handles=handles, title="Daily Irradiation [kWh/m2]", loc='best', frameon = False, bbox_to_anchor=(0.2, .9), ncol=4)
    lineLegend = plt.legend(loc = 'center', frameon = False)

    # Calculating averages
    avg_pr_7d = csvData['PR'].tail(7).mean()
    avg_pr_30d = csvData['PR'].tail(30).mean()
    avg_pr_60d = csvData['PR'].tail(60).mean()
    avg_pr_90d = csvData['PR'].tail(90).mean()
    avg_pr_365d = csvData['PR'].tail(365).mean()
    avg_pr_lifetime = csvData['PR'].mean()

    # Calculate the positions
    ax = plt.gca()
    x_position = ax.get_xlim()[1] # Near the right edge
    y_position_start = 30  # Start from 35% from the bottom

    # Positioning the average PR values inside the plot
    plt.text(x_position, y_position_start, f'Average PR last 7-d: {avg_pr_7d:.2f} %', fontsize=10, verticalalignment='top', horizontalalignment='right')
    plt.text(x_position, y_position_start - 5, f'Average PR last 30-d: {avg_pr_30d:.2f} %', fontsize=10, verticalalignment='top', horizontalalignment='right')
    plt.text(x_position, y_position_start - 10, f'Average PR last 60-d: {avg_pr_60d:.2f} %', fontsize=10, verticalalignment='top', horizontalalignment='right')
    plt.text(x_position, y_position_start - 15, f'Average PR last 90-d: {avg_pr_90d:.2f} %', fontsize=10, verticalalignment='top', horizontalalignment='right')
    plt.text(x_position, y_position_start - 20, f'Average PR last 365-d: {avg_pr_365d:.2f} %', fontsize=10, verticalalignment='top', horizontalalignment='right')
    plt.text(x_position, y_position_start - 25, f'Average PR Lifetime: {avg_pr_lifetime:.2f} %', fontsize=10, fontweight='bold', verticalalignment='top', horizontalalignment='right')


    plt.yticks(range(0, 101, 10))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    
    # Labels for x and y axes
    plt.xlabel('Date')
    plt.ylabel('Performance Ratio [%]')
    plt.title(f'Performance Ratio Evolution\nFrom {startDate.date()} to {endDate.date()}', fontweight='bold')

    plt.gca().add_artist(scatterLegend)
    
    # Saving JPEG
    plt.savefig(f'plot_{str(startDate.date())}_to_{str(endDate.date())}.jpg', dpi=300, bbox_inches='tight')

    # Show the plot
    plt.show()


if __name__ == '__main__':
    main()
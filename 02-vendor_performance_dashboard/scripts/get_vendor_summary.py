
import pandas as pd

import logging 
from scripts.ingestion_db import ingest_db
import sys
import duckdb

logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level = logging.DEBUG,
    format= "%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

def create_vendor_summary(con):
    """ This function will merge the different tables to get the overall vendor summary and adding new columns in the result data
    """
    vendor_sales_summary = con.execute("""

                WITH FreightSummary AS (

                    SELECT
                        VendorNumber,
                        SUM(Freight) AS FreightCost
                    FROM vendor_invoice
                    GROUP BY VendorNumber
                ),

                PurchaseSummary AS (

                    SELECT
                        VendorNumber,
                        VendorName,
                        Brand,
                        Description,
                        PurchasePrice,
                        SUM(Quantity) AS TotalPurchaseQuantity,
                        SUM(Dollars) AS TotalPurchaseDollars
                    FROM purchases
                    WHERE PurchasePrice > 0
                    GROUP BY
                        VendorNumber,
                        VendorName,
                        Brand,
                        Description,
                        PurchasePrice
                ),

                PriceSummary AS (

                    SELECT
                        Brand,
                        Description,
                        MAX(Price) AS ActualPrice,
                        MAX(Volume) AS Volume
                    FROM purchase_prices
                    GROUP BY Brand, Description
                ),

                SalesSummary AS (

                    SELECT
                        VendorNo,
                        Brand,

                        SUM(SalesQuantity) AS TotalSalesQuantity,
                        SUM(SalesDollars) AS TotalSalesDollars,
                        SUM(SalesPrice) AS TotalSalesPrice,
                        SUM(ExciseTax) AS TotalExciseTax

                    FROM sales

                    GROUP BY VendorNo, Brand
                )

                SELECT

                    ps.VendorNumber,
                    ps.VendorName,
                    ps.Brand,
                    ps.Description,

                    ps.PurchasePrice,

                    prs.ActualPrice,
                    prs.Volume,

                    ps.TotalPurchaseQuantity,
                    ps.TotalPurchaseDollars,

                    COALESCE(ss.TotalSalesQuantity, 0) AS TotalSalesQuantity,
                    COALESCE(ss.TotalSalesDollars, 0) AS TotalSalesDollars,
                    COALESCE(ss.TotalSalesPrice, 0) AS TotalSalesPrice,
                    COALESCE(ss.TotalExciseTax, 0) AS TotalExciseTax,

                    COALESCE(fs.FreightCost, 0) AS FreightCost

                FROM PurchaseSummary ps

                LEFT JOIN PriceSummary prs
                    ON ps.Brand = prs.Brand
                AND ps.Description = prs.Description

                LEFT JOIN SalesSummary ss
                    ON ps.VendorNumber = ss.VendorNo
                AND ps.Brand = ss.Brand

                LEFT JOIN FreightSummary fs
                    ON ps.VendorNumber = fs.VendorNumber

                ORDER BY ps.TotalPurchaseDollars DESC

                """).fetchdf()

    return vendor_sales_summary


    
def clean_data(df):
    print(df.dtypes)
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    numeric_cols = [
        'TotalSalesDollars',
        'TotalPurchaseDollars',
        'TotalSalesQuantity',
        'TotalPurchaseQuantity'
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # New KPIs
    df['GrossProfit'] = (
        df['TotalSalesDollars'] - df['TotalPurchaseDollars']
    )

    df['ProfitMargin'] = (
        df['GrossProfit'] / df['TotalSalesDollars']
    ) * 100

    df['StockTurnover'] = (
        df['TotalSalesQuantity'] / df['TotalPurchaseQuantity']
    )

    df['SalestoPurchaseRatio'] = (
        df['TotalSalesDollars'] / df['TotalPurchaseDollars']
    )

    return df




if __name__ =='__main__':
    #creating database connection
    con = duckdb.connect("inventory.db")

    logging.info('Creating vendor Summary Table.....')
    summary_df = create_vendor_summary(con)
    logging.info(summary_df.head())

    logging.info("Cleaning Data....")
    clean_df = clean_data(summary_df)
    logging.info(clean_df.head())

    logging.info('Ingesting data.....')
    ingest_db(clean_df,'vendor_sales_summary',con)
    logging.info('Completed')

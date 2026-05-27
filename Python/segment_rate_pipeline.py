# === MODULE 1: Download Latest HQM File ===
import requests
from datetime import datetime

def download_latest_hqm():
    """
    Downloads the latest HQM .xls file from the Treasury website using the current date.
    Saves it to the 'hqm_data/' folder with filename format 'hqm_YY_MM.xls'.
    """
    today = datetime.today()
    filename = f"hqm_{today.strftime('%y_%m')}.xls"
    url = f"https://www.treasury.gov/resource-center/economic-policy/Documents/{filename}"
    response = requests.get(url)

    if response.status_code == 200:
        with open(f"hqm_data/{filename}", "wb") as f:
            f.write(response.content)
        print(f"✅ Downloaded: {filename}")
    else:
        print(f"❌ Failed to download HQM file. Status code: {response.status_code}")

# === MODULE 2: Extract Segment Rates from XLS Files ===
import pandas as pd
import glob
import os

def extract_segment_rates():
    """
    Reads all HQM .xls files in 'hqm_data/'.
    Extracts yield curve data, computes average yields for Segment 1 (0.5–5.5 yrs),
    Segment 2 (6–20.5 yrs), and Segment 3 (>20.5 yrs).
    Returns a sorted DataFrame with columns: Month, Seg1, Seg2, Seg3.
    """
    files = sorted(glob.glob('hqm_data/*.xls'))
    segment_data = []

    for file in files:
        try:
            df = pd.read_excel(file, skiprows=1)
            yields = df.iloc[0, 1:]  # Skip first column (maturity labels)
            seg1 = yields[0:11].mean()
            seg2 = yields[11:41].mean()
            seg3 = yields[41:].mean()
            month_str = os.path.basename(file).split('_')[-1].replace('.xls', '')
            segment_data.append([month_str, seg1, seg2, seg3])
        except Exception as e:
            print(f"⚠️ Error processing {file}: {e}")

    df_segments = pd.DataFrame(segment_data, columns=['Month', 'Seg1', 'Seg2', 'Seg3'])
    df_segments['Month'] = pd.to_datetime(df_segments['Month'], format='%y_%m')
    df_segments.sort_values('Month', inplace=True)
    df_segments.to_csv('segment_rates.csv', index=False)
    return df_segments

# === MODULE 3: Predict Next Month’s Segment Rates ===
from sklearn.linear_model import LinearRegression
import numpy as np

def predict_next(df_segments):
    """
    Performs simple linear regression on each segment column to predict next month's rate.
    Returns a dictionary with keys: 'Seg1', 'Seg2', 'Seg3' and predicted float values.
    """
    X = np.arange(len(df_segments)).reshape(-1, 1)
    predictions = {}

    for col in ['Seg1', 'Seg2', 'Seg3']:
        model = LinearRegression().fit(X, df_segments[col])
        predictions[col] = model.predict([[len(df_segments)]])[0]

    return predictions

# === MODULE 4: Export to Excel ===
from openpyxl import load_workbook

def export_to_excel(df_segments, predictions, filename='segment_rates.xlsx'):
    """
    Exports the historical segment rates to 'Historical' sheet,
    and predicted next-month rates to 'Predicted' sheet in the same Excel file.
    """
    df_segments.to_excel(filename, index=False, sheet_name='Historical')

    with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        pred_df = pd.DataFrame([predictions], columns=['Seg1', 'Seg2', 'Seg3'])
        pred_df.index = ['Next Month']
        pred_df.to_excel(writer, sheet_name='Predicted')

# === MODULE 5: Main Runner ===
if __name__ == "__main__":
    print("📥 Step 1: Downloading latest HQM file...")
    download_latest_hqm()

    print("📊 Step 2: Extracting segment rates...")
    df_segments = extract_segment_rates()

    print("📈 Step 3: Predicting next month’s rates...")
    predictions = predict_next(df_segments)

    print("📤 Step 4: Exporting to Excel...")
    export_to_excel(df_segments, predictions)

    print("\n✅ All done. Segment rates saved to 'segment_rates.xlsx'.")
    print("📉 Predicted Rates:")
    for seg, rate in predictions.items():
        print(f"{seg}: {rate:.4%}")

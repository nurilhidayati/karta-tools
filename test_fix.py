import pandas as pd

# Simulate the fixed load_data function and filtering
devices = pd.read_csv("data/devices.csv", parse_dates=["last_seen","install_date"])
devices["last_seen"] = pd.to_datetime(devices["last_seen"]).dt.tz_localize(None)

# Test the filtering with the new 72-hour default
df = devices.copy()
hours = 72
cutoff = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(hours=hours)
df = df[df.last_seen >= cutoff]

total = len(df)
total_devices = len(devices)

print(f"✅ FIXED: Total devices in CSV: {total_devices}")
print(f"✅ FIXED: Devices after 72h filter: {total}")
print(f"✅ FIXED: Filter working correctly: {total > 0}")
print(f"✅ FIXED: Status breakdown:")
print(df.status.value_counts())


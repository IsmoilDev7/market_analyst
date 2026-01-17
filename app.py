import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="Zakaz & Sotuv Analitika", layout="wide")

# ================================
# UNIVERSAL FILE LOADER
# ================================
def load_file(uploaded_file):
    if uploaded_file is None:
        return None

    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    try:
        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))
        if name.endswith(".xlsx"):
            return pd.read_excel(BytesIO(data), engine="openpyxl")
        if name.endswith(".xls"):
            return pd.read_excel(BytesIO(data))
    except Exception as e:
        st.error(f"❌ Faylni o‘qishda xatolik: {e}")
        return None

    st.error("❌ Noto‘g‘ri fayl formati")
    return None

# ================================
# FILE UPLOAD
# ================================
st.title("📊 Zakaz – Sotuv – Qaytish Analitik Dashboard")

orders_file = st.file_uploader("1️⃣ Zakaz fayli", type=["xlsx","xls","csv"])
sales_file  = st.file_uploader("2️⃣ Sotuv / Qaytish fayli", type=["xlsx","xls","csv"])

if not orders_file or not sales_file:
    st.info("Ikkala faylni ham yuklang")
    st.stop()

orders = load_file(orders_file)
sales  = load_file(sales_file)

if orders is None or sales is None:
    st.stop()

st.success("✅ Fayllar muvaffaqiyatli yuklandi")

# ================================
# SAFE COLUMN NORMALIZATION
# ================================
def safe_col(df, col):
    if col not in df.columns:
        df[col] = 0
    return df

orders_cols = ["Количество", "Сумма", "Контрагент", "Номенклатура", "Период"]
sales_cols  = ["Количество", "Продажная сумма", "Возврат сумма", "Номенклатура", "Контрагент", "Период"]

for c in orders_cols: orders = safe_col(orders, c)
for c in sales_cols:  sales  = safe_col(sales, c)

# Convert to datetime
orders["Период"] = pd.to_datetime(orders["Период"], errors="coerce")
sales["Период"]  = pd.to_datetime(sales["Период"], errors="coerce")

# ================================
# FIXED DATE FILTER: 01.12.2025 - 30.12.2025
# ================================
date_from = pd.to_datetime("2025-12-01")
date_to   = pd.to_datetime("2025-12-30")

orders = orders[(orders["Период"] >= date_from) & (orders["Период"] <= date_to)]
sales  = sales[(sales["Периod"] >= date_from) & (sales["Периod"] <= date_to)]

# ================================
# KPI BLOCK
# ================================
st.subheader("📌 Asosiy ko‘rsatkichlar")

total_orders = orders["Количество"].sum()
total_sales  = sales["Продажная сумма"].sum()
total_return = sales["Возврат сумма"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("🧾 Zakaz miqdori", f"{total_orders:,.0f}")
c2.metric("💰 Sotuv summasi", f"{total_sales:,.0f}")
c3.metric("↩️ Qaytgan summa", f"{total_return:,.0f}")
c4.metric(
    "❌ Qaytish %",
    f"{min((total_return / max(total_sales,1)*100), 100):.2f}%"
)

# ================================
# PRODUCT ANALYSIS
# ================================
st.subheader("🛒 Mahsulot bo‘yicha analiz")

prod_orders = orders.groupby("Номенклатура")["Количество"].sum()
prod_sales  = sales.groupby("Номенклатура")["Продажная сумма"].sum()
prod_return = sales.groupby("Номенклатура")["Возврат сумма"].sum()

summary = pd.concat([prod_orders, prod_sales, prod_return], axis=1).fillna(0)
summary.columns = ["Zakaz","Sotuv","Qaytish"]
summary["Return_%"] = (summary["Qaytish"] / summary["Sotuv"].replace(0,1)*100).clip(upper=100).round(2)

st.dataframe(summary.sort_values("Return_%", ascending=False), use_container_width=True)

# ================================
# ZARARLI MAHSULOTLAR
# ================================
st.subheader("🚨 Zarar keltirayotgan mahsulotlar")
loss_products = summary[(summary["Return_%"] > 20) & (summary["Qaytish"] > 0)]
st.dataframe(loss_products, use_container_width=True)

# ================================
# CLIENT ANALYSIS
# ================================
st.subheader("👤 Klientlar kesimida analiz")
client_orders  = orders.groupby("Контрагент")["Количество"].sum()
client_returns = sales.groupby("Контрагент")["Возврат сумма"].sum()

client_df = pd.concat([client_orders, client_returns], axis=1).fillna(0)
client_df.columns = ["Zakaz","Qaytish"]
client_df["Qaytish_%"] = (client_df["Qaytish"]/client_df["Zakaz"].replace(0,1)*100).clip(upper=100).round(2)
st.dataframe(client_df.sort_values("Qaytish_%", ascending=False), use_container_width=True)

# ================================
# WEEKDAY ANALYSIS
# ================================
st.subheader("📆 Hafta kunlari bo‘yicha zakaz & qaytish")

orders["weekday"] = orders["Период"].dt.day_name()
sales["weekday"]  = sales["Периod"].dt.day_name()

week_order  = orders.groupby("weekday")["Количество"].sum()
week_return = sales.groupby("weekday")["Возврат сумма"].sum()

# Sort weekdays to Monday-Sunday
weekdays_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
week_order = week_order.reindex(weekdays_order).fillna(0)
week_return = week_return.reindex(weekdays_order).fillna(0)

fig, ax = plt.subplots(figsize=(10,5))
week_order.plot(kind="bar", ax=ax, color='skyblue')
ax.set_title("Zakazlar – hafta kunlari")
st.pyplot(fig)

fig2, ax2 = plt.subplots(figsize=(10,5))
week_return.plot(kind="bar", ax=ax2, color='salmon')
ax2.set_title("Qaytishlar – hafta kunlari")
st.pyplot(fig2)

# ================================
# SIMPLE FORECAST
# ================================
st.subheader("📈 Zakaz prognozi (oddiy)")

daily = orders.groupby(orders["Периod"].dt.date)["Количество"].sum()
forecast = daily.rolling(3).mean()

fig3, ax3 = plt.subplots(figsize=(10,5))
daily.plot(ax=ax3, label="Real", marker='o')
forecast.plot(ax=ax3, label="Prognoz", linestyle='--')
ax3.legend()
st.pyplot(fig3)

st.success("✅ Analiz to‘liq yakunlandi")

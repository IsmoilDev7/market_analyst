import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="Zakaz & Sotuv Analitika", layout="wide")

# ================================
# UNIVERSAL EXCEL / CSV LOADER
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
            try:
                return pd.read_excel(BytesIO(data), engine="openpyxl")
            except Exception:
                return pd.read_excel(BytesIO(data))
        if name.endswith(".xls"):
            return pd.read_excel(BytesIO(data))
    except Exception as e:
        st.error(f"❌ Faylni o‘qishda xatolik: {e}")
        return None

    st.error("❌ Noto‘g‘ri fayl formati")
    return None


# ================================
# UI
# ================================
st.title("📊 Zakaz – Sotuv – Qaytish Analitik Dashboard")

orders_file = st.file_uploader("1️⃣ Zakaz fayli", type=["xlsx", "xls", "csv"])
sales_file  = st.file_uploader("2️⃣ Sotuv / Qaytish fayli", type=["xlsx", "xls", "csv"])

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

orders = safe_col(orders, "Количество")
orders = safe_col(orders, "Сумма")
orders = safe_col(orders, "Контрагент")
orders = safe_col(orders, "Номенклатура")
orders = safe_col(orders, "Период")

sales = safe_col(sales, "Количество")
sales = safe_col(sales, "Продажная сумма")
sales = safe_col(sales, "Возврат сумма")
sales = safe_col(sales, "Номенклатура")
sales = safe_col(sales, "Контрагент")
sales = safe_col(sales, "Период")

orders["Период"] = pd.to_datetime(orders["Период"], errors="coerce")
sales["Период"]  = pd.to_datetime(sales["Период"], errors="coerce")

# ================================
# DATE + TIME FILTER
# ================================
min_date = min(orders["Период"].min(), sales["Период"].min())
max_date = max(orders["Период"].max(), sales["Период"].max())

date_from, date_to = st.date_input(
    "📅 Sana oralig‘i",
    [min_date.date(), max_date.date()]
)

time_from = st.time_input("⏰ Boshlanish vaqti", value=pd.to_datetime("00:00").time())
time_to   = st.time_input("⏰ Tugash vaqti", value=pd.to_datetime("23:59").time())

orders = orders[
    (orders["Период"] >= pd.to_datetime(date_from)) &
    (orders["Период"] <= pd.to_datetime(date_to)) &
    (orders["Период"].dt.time >= time_from) &
    (orders["Период"].dt.time <= time_to)
]

sales = sales[
    (sales["Период"] >= pd.to_datetime(date_from)) &
    (sales["Период"] <= pd.to_datetime(date_to)) &
    (sales["Период"].dt.time >= time_from) &
    (sales["Период"].dt.time <= time_to)
]

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
    f"{min((total_return / max(total_sales, 1) * 100), 100):.2f}%"
)

# ================================
# PRODUCT ANALYSIS
# ================================
st.subheader("🛒 Mahsulot bo‘yicha analiz")

prod_orders = orders.groupby("Номенклатура")["Количество"].sum()
prod_sales  = sales.groupby("Номенклатура")["Продажная summa"].sum()
prod_return = sales.groupby("Номенклатура")["Возврат сумма"].sum()

summary = pd.concat([prod_orders, prod_sales, prod_return], axis=1).fillna(0)
summary.columns = ["Zakaz", "Sotuv", "Qaytish"]

summary["Return_%"] = (
    summary["Qaytish"] / summary["Sotuv"].replace(0, 1) * 100
).clip(upper=100).round(2)

st.dataframe(summary.sort_values("Return_%", ascending=False), use_container_width=True)

# ================================
# CLIENT ANALYSIS
# ================================
st.subheader("👤 Klientlar kesimida analiz")

client_orders = orders.groupby("Контрагент")["Количество"].sum()
client_returns = sales.groupby("Контрагент")["Возврат сумма"].sum()

client_df = pd.concat([client_orders, client_returns], axis=1).fillna(0)
client_df.columns = ["Zakaz", "Qaytish"]

client_df["Qaytish_%"] = (
    client_df["Qaytish"] / client_df["Zakaz"].replace(0, 1) * 100
).clip(upper=100).round(2)

st.dataframe(
    client_df.sort_values("Qaytish_%", ascending=False),
    use_container_width=True
)

# ================================
# SIMPLE FORECAST
# ================================
st.subheader("📈 Zakaz prognozi (oddiy)")

daily = orders.groupby(orders["Период"].dt.date)["Количество"].sum()
forecast = daily.rolling(3).mean()

fig, ax = plt.subplots(figsize=(10,5))
daily.plot(ax=ax, label="Real")
forecast.plot(ax=ax, label="Prognoz")
ax.legend()
st.pyplot(fig)

st.success("✅ Analiz to‘liq yakunlandi")

import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="Zakaz Analitika", layout="wide")

# =========================
# UNIVERSAL FILE LOADER
# =========================
def load_file(file):
    name = file.name.lower()
    data = file.read()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))
        else:
            return pd.read_excel(BytesIO(data), engine="openpyxl")
    except Exception:
        try:
            return pd.read_excel(BytesIO(data))
        except Exception as e:
            st.error(f"Fayl o‘qilmadi: {e}")
            return None

# =========================
# SAFE COLUMN CREATOR
# =========================
def col(df, name):
    if name not in df.columns:
        df[name] = 0
    return df

# =========================
# UI
# =========================
st.title("📊 Zakaz – Sotuv – Qaytish Analitika")

orders_file = st.file_uploader("📥 Zakaz fayli", ["xlsx", "xls", "csv"])
sales_file  = st.file_uploader("📥 Sotuv / Qaytish fayli", ["xlsx", "xls", "csv"])

if not orders_file or not sales_file:
    st.stop()

orders = load_file(orders_file)
sales  = load_file(sales_file)

if orders is None or sales is None:
    st.stop()

# =========================
# NORMALIZATION
# =========================
orders = col(orders, "Количество")
orders = col(orders, "Контрагент")
orders = col(orders, "Номенклатура")
orders = col(orders, "Период")

sales = col(sales, "Продажная сумма")
sales = col(sales, "Возврат сумма")
sales = col(sales, "Контрагент")
sales = col(sales, "Номенклатура")
sales = col(sales, "Период")

orders["Период"] = pd.to_datetime(orders["Период"], errors="coerce")
sales["Период"]  = pd.to_datetime(sales["Период"], errors="coerce")

# =========================
# DATE FILTER
# =========================
min_date = min(orders["Период"].min(), sales["Период"].min())
max_date = max(orders["Период"].max(), sales["Период"].max())

date_from, date_to = st.date_input(
    "📅 Sana oralig‘i",
    [min_date.date(), max_date.date()]
)

orders = orders[(orders["Период"] >= pd.to_datetime(date_from)) &
                (orders["Период"] <= pd.to_datetime(date_to))]

sales = sales[(sales["Период"] >= pd.to_datetime(date_from)) &
              (sales["Период"] <= pd.to_datetime(date_to))]

# =========================
# CLIENT ANALYSIS (FIXED)
# =========================
st.subheader("👤 Klientlar kesimida QAYTISH ANALIZI")

client_orders = orders.groupby("Контрагент")["Количество"].sum()
client_sales  = sales.groupby("Контрагент")["Продажная сумма"].sum()
client_return = sales.groupby("Контрагент")["Возврат сумма"].sum()

client_df = pd.concat(
    [client_orders, client_sales, client_return],
    axis=1
).fillna(0)

client_df.columns = ["Zakaz_soni", "Sotuv_summa", "Qaytish_summa"]

# 🔒 FOIZNI TO‘G‘RI HISOBLASH (0–100)
client_df["Qaytish_%"] = (
    client_df["Qaytish_summa"] /
    client_df["Sotuv_summa"].replace(0, 1)
) * 100

client_df["Qaytish_%"] = client_df["Qaytish_%"].clip(0, 100).round(2)

st.dataframe(
    client_df.sort_values("Qaytish_%", ascending=False),
    use_container_width=True
)

# =========================
# VISUAL
# =========================
st.subheader("📉 Eng ko‘p qaytish bo‘lgan klientlar")

top = client_df.sort_values("Qaytish_%", ascending=False).head(10)

fig, ax = plt.subplots(figsize=(10,5))
top["Qaytish_%"].plot(kind="bar", ax=ax)
ax.set_ylabel("%")
ax.set_title("Top 10 klient – Qaytish foizi")
st.pyplot(fig)

st.success("✅ Barcha analizlar xatosiz yakunlandi")

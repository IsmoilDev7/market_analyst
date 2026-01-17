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
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(BytesIO(data), engine="openpyxl")
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

# Orders
orders = safe_col(orders, "Количество")
orders = safe_col(orders, "Сумма")
orders = safe_col(orders, "Контрагент")
orders = safe_col(orders, "Номенклатура")
orders = safe_col(orders, "Период")

# Sales
sales = safe_col(sales, "Количество")
sales = safe_col(sales, "Продажная сумма")
sales = safe_col(sales, "Возврат сумма")
sales = safe_col(sales, "Номенклатура")
sales = safe_col(sales, "Контрагент")

# ================================
# DATE COLUMN FIX
# ================================
# Orders
if "Период" not in orders.columns:
    st.error("❌ Orders faylida 'Период' ustuni topilmadi!")
    st.stop()
orders["Период"] = pd.to_datetime(orders["Период"], errors="coerce")

# Sales
if "Период" not in sales.columns and "Периod" in sales.columns:
    sales.rename(columns={"Периod":"Период"}, inplace=True)
elif "Период" not in sales.columns:
    st.error("❌ Sales faylida 'Период' ustuni topilmadi!")
    st.stop()
sales["Период"] = pd.to_datetime(sales["Период"], errors="coerce")

# ================================
# INTERACTIVE DATE FILTER
# ================================
min_date = min(orders["Период"].min(), sales["Период"].min())
max_date = max(orders["Период"].max(), sales["Период"].max())

date_range = st.date_input(
    "📅 Sana oralig‘i tanlang",
    value=[min_date.date(), max_date.date()],
    min_value=min_date.date(),
    max_value=max_date.date()
)
if len(date_range) !=2:
    st.error("❌ Iltimos, boshlanish va tugash sanasini tanlang")
    st.stop()

date_from = pd.to_datetime(date_range[0])
date_to   = pd.to_datetime(date_range[1])

orders = orders[(orders["Период"] >= date_from) & (orders["Период"] <= date_to)]
sales  = sales[(sales["Период"] >= date_from) & (sales["Период"] <= date_to)]

# ================================
# KPI BLOCK
# ================================
st.subheader("📌 Asosiy ko‘rsatkichlar")
total_orders = orders["Количество"].sum()
total_sales  = sales["Продажная сумма"].sum()
total_return = sales["Возврат сумма"].sum()

c1,c2,c3,c4 = st.columns(4)
c1.metric("🧾 Zakaz miqdori", f"{total_orders:,.0f}")
c2.metric("💰 Sotuv summasi", f"{total_sales:,.0f}")
c3.metric("↩️ Qaytgan summa", f"{total_return:,.0f}")
c4.metric("❌ Qaytish %", f"{min((total_return/max(total_sales,1)*100),100):.2f}%")

# ================================
# PRODUCT ANALYSIS
# ================================
st.subheader("🛒 Mahsulot bo‘yicha analiz")
prod_orders = orders.groupby("Номенклатура")["Количество"].sum()
prod_sales  = sales.groupby("Номенклатура")["Продажная сумма"].sum()
prod_return = sales.groupby("Номенклатура")["Возврат сумма"].sum()

summary = pd.concat([prod_orders, prod_sales, prod_return], axis=1).fillna(0)
summary.columns = ["Zakaz","Sotuv","Qaytish"]
summary["Return_%"] = (summary["Qaytish"]/summary["Sotuv"].replace(0,1)*100).clip(upper=100).round(2)

st.dataframe(summary.sort_values("Return_%", ascending=False), use_container_width=True)

# ================================
# LOSS PRODUCTS
# ================================
st.subheader("🚨 Zarar keltirayotgan mahsulotlar")
loss_products = summary[(summary["Return_%"]>20) & (summary["Qaytish"]>0)]
st.dataframe(loss_products, use_container_width=True)

# ================================
# CLIENT ANALYSIS
# ================================
st.subheader("👤 Klientlar kesimida analiz")
client_orders  = orders.groupby("Контрагент")["Количество"].sum()
client_returns = sales.groupby("Контрагент")["Возврат сумма"].sum()
client_df = pd.concat([client_orders,client_returns],axis=1).fillna(0)
client_df.columns=["Zakaz","Qaytish"]
client_df["Qaytish_%"] = (client_df["Qaytish"]/client_df["Zakaz"].replace(0,1)*100).clip(upper=100).round(2)
st.dataframe(client_df.sort_values("Qaytish_%",ascending=False), use_container_width=True)

# ================================
# WEEKDAY ANALYSIS
# ================================
st.subheader("📆 Hafta kunlari bo‘yicha zakaz & qaytish")
orders["weekday"] = orders["Период"].dt.day_name()
sales["weekday"]  = sales["Периod"].dt.day_name()  # ustun nomi to‘g‘rilandi

week_order  = orders.groupby("weekday")["Количество"].sum().reindex(
    ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]).fillna(0)
week_return = sales.groupby("weekday")["Возврат сумма"].sum().reindex(
    ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]).fillna(0)

fig,ax=plt.subplots(figsize=(10,5))
week_order.plot(kind="bar",ax=ax,color='skyblue')
ax.set_title("Zakazlar – hafta kunlari")
st.pyplot(fig)

fig2,ax2=plt.subplots(figsize=(10,5))
week_return.plot(kind="bar",ax=ax2,color='salmon')
ax2.set_title("Qaytishlar – hafta kunlari")
st.pyplot(fig2)

# ================================
# SIMPLE FORECAST
# ================================
st.subheader("📈 Zakaz prognozi (oddiy 3 kunlik)")
daily = orders.groupby(orders["Период"].dt.date)["Количество"].sum()
forecast = daily.rolling(3).mean()

fig3,ax3=plt.subplots(figsize=(10,5))
daily.plot(ax=ax3,label="Real",marker='o')
forecast.plot(ax=ax3,label="Prognoz",marker='x')
ax3.legend()
st.pyplot(fig3)

st.success("✅ Analiz to‘liq yakunlandi")

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="Zakaz & Sotuv Analitika", layout="wide")

# =========================
# UNIVERSAL FILE LOADER
# =========================
def load_any_excel(uploaded_file):
    try:
        name = uploaded_file.name.lower()
        data = uploaded_file.read()

        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            try:
                return pd.read_excel(BytesIO(data), engine="openpyxl")
            except:
                return pd.read_excel(BytesIO(data))
        else:
            st.error("Noto‘g‘ri format")
            return None
    except Exception as e:
        st.error(f"Faylni o‘qishda xato: {e}")
        return None

# =========================
# UI
# =========================
st.title("📊 Zakaz – Sotuv – Qaytish – Prognoz Analitika")

orders_file = st.file_uploader("📁 Zakaz Excel", type=["xlsx","xls","csv"])
sales_file  = st.file_uploader("📁 Sotuv / Qaytish Excel", type=["xlsx","xls","csv"])

if orders_file and sales_file:
    orders = load_any_excel(orders_file)
    sales  = load_any_excel(sales_file)

    if orders is None or sales is None:
        st.stop()

    # =========================
    # DATA CLEANING
    # =========================
    for df in [orders, sales]:
        df["Период"] = pd.to_datetime(df["Период"], errors="coerce")

    numeric_cols = [
        "Количество", "Сумма",
        "Продажная сумма", "Себестоимость сумма",
        "Возврат количество"
    ]

    for col in numeric_cols:
        if col in sales.columns:
            sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0)
        if col in orders.columns:
            orders[col] = pd.to_numeric(orders[col], errors="coerce").fillna(0)

    # =========================
    # DATE FILTER (TIME INCLUDED)
    # =========================
    st.sidebar.header("📅 Sana & vaqt filter")

    start = st.sidebar.datetime_input(
        "Boshlanish",
        value=orders["Период"].min()
    )
    end = st.sidebar.datetime_input(
        "Tugash",
        value=orders["Период"].max()
    )

    orders = orders[(orders["Период"] >= start) & (orders["Период"] <= end)]
    sales  = sales[(sales["Период"] >= start) & (sales["Период"] <= end)]

    # =========================
    # 1. ORDER EXECUTION
    # =========================
    st.header("1️⃣ Zakaz bajarilishi")

    order_summary = orders.groupby("Номенклатура")["Количество"].sum()
    delivered = sales.groupby("Номенклатура")["Количество"].sum()
    returned  = sales.groupby("Номенклатура")["Возврат количество"].sum()

    exec_df = pd.concat([order_summary, delivered, returned], axis=1).fillna(0)
    exec_df.columns = ["Zakaz", "Yetkazilgan", "Qaytgan"]
    exec_df["Bajarilish %"] = (exec_df["Yetkazilgan"] / exec_df["Zakaz"] * 100).round(2)

    st.dataframe(exec_df)

    # =========================
    # 2. WEEKDAY ANALYSIS
    # =========================
    st.header("2️⃣ Hafta kunlari bo‘yicha analiz")

    orders["Weekday"] = orders["Период"].dt.day_name()
    weekday = orders.groupby(["Weekday","Номенклатура"])["Количество"].sum().reset_index()

    st.dataframe(weekday)

    # =========================
    # 3. CLIENT ANALYSIS
    # =========================
    st.header("3️⃣ Klientlar kesimida")

    client_df = orders.groupby(["Контрагент","Номенклатура"])["Количество"].sum().reset_index()
    st.dataframe(client_df)

    # =========================
    # 4. DAMAGE / LOSS ANALYSIS
    # =========================
    st.header("4️⃣ ZARAR KELTIRAYOTGAN MAHSULOTLAR")

    profit_df = sales.groupby("Номенклатура").agg({
        "Продажная сумма":"sum",
        "Себестоимость сумма":"sum",
        "Возврат сумма":"sum" if "Возврат сумма" in sales.columns else "sum"
    }).fillna(0)

    profit_df["Profit"] = (
        profit_df["Продажная сумма"]
        - profit_df["Себестоимость сумма"]
        - profit_df.get("Возврат сумма",0)
    )

    loss_products = profit_df[profit_df["Profit"] < 0]
    st.dataframe(loss_products)

    # =========================
    # 5. SIMPLE FORECAST
    # =========================
    st.header("5️⃣ Zakaz prognozi (oddiy)")

    daily = orders.groupby(orders["Период"].dt.date)["Количество"].sum()
    avg = daily.mean()

    forecast = pd.DataFrame({
        "Keyingi kun prognozi":[round(avg,2)]
    })

    st.dataframe(forecast)

    st.success("✅ Analiz yakunlandi")

import streamlit as st
import pandas as pd
from datetime import datetime, date
import re
from fpdf import FPDF
import os
import pickle
import io

st.set_page_config(
    page_title="(주)로프트프라퍼티스 입출금 관리",
    page_icon="🏢",
    layout="wide"
)

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "transactions.pkl")

INCOME_CATEGORIES = ["임대수입", "관리비수입", "보증금", "기타수입"]
EXPENSE_CATEGORIES = ["인건비", "세금", "관리용역비", "공과금", "수선유지비", "금융비용", "기타지출"]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

FIXED_UNITS = [
    "100호", "101호", "102호", "103호", "104호",
    "201호", "202호", "203호", "204호", "205호", "206호", "207호", "208호",
    "301호", "302호", "303호", "304호",
    "401호", "402호", "403호", "404호", "405호", "406호", "407호", "408호",
    "601호", "602호", "603호", "604호", "605호", "606호", "607호", "608호"
]

def save_data(df):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "wb") as f:
            pickle.dump(df, f)
    except Exception as e:
        st.warning(f"데이터 저장 실패 (클라우드 환경일 수 있음): {e}")

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                return pickle.load(f)
        except:
            pass
    return pd.DataFrame(columns=[
        "거래일시", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도", "카테고리", "호수"
    ])

def extract_unit(memo):
    if pd.isna(memo) or str(memo).strip() == "":
        return "미지정"
    text = str(memo).strip()
    match = re.search(r'(\d+)\s*호', text)
    if match:
        return f"{match.group(1)}호"
    match = re.search(r'\b(\d{2,4})\b', text)
    if match:
        return f"{match.group(1)}호"
    match = re.search(r'([A-Za-z가-힣]*동)\s*(\d+)\s*호?', text)
    if match:
        return f"{match.group(1)} {match.group(2)}호"
    return "미지정"

def assign_category(row):
    return "미분류"

def process_uploaded_df(new_df):
    required_cols = ["거래일시", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도"]
    missing = [c for c in required_cols if c not in new_df.columns]
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")

    cols = required_cols.copy()
    if "카테고리" in new_df.columns:
        cols.append("카테고리")
    if "호수" in new_df.columns:
        cols.append("호수")

    new_df = new_df[cols].copy()
    new_df["거래일시"] = pd.to_datetime(new_df["거래일시"], errors="coerce")
    new_df["출금액"] = pd.to_numeric(new_df["출금액"], errors="coerce").fillna(0)
    new_df["입금액"] = pd.to_numeric(new_df["입금액"], errors="coerce").fillna(0)
    new_df["잔액"] = pd.to_numeric(new_df["잔액"], errors="coerce")
    new_df["년도"] = new_df["년도"].astype(str)

    if "카테고리" not in new_df.columns:
        new_df["카테고리"] = "미분류"
    else:
        new_df["카테고리"] = new_df["카테고리"].fillna("미분류").astype(str)

    if "호수" not in new_df.columns:
        new_df["호수"] = new_df["송금메모"].apply(extract_unit)
    else:
        mask_empty = new_df["호수"].isna() | (new_df["호수"].astype(str).str.strip() == "") | (new_df["호수"].astype(str) == "nan")
        new_df.loc[mask_empty, "호수"] = new_df.loc[mask_empty, "송금메모"].apply(extract_unit)
        new_df["호수"] = new_df["호수"].astype(str)

    return new_df

def create_pdf(df, title="Transaction Report", unit="선택안함", party="선택안함", search=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    use_korean = False
    font_name = "Helvetica"
    try:
        pdf.add_font("Malgun", "", r"C:\Windows\Fonts\malgun.ttf", uni=True)
        pdf.add_font("Malgun", "B", r"C:\Windows\Fonts\malgunbd.ttf", uni=True)
        font_name = "Malgun"
        use_korean = True
    except:
        pass

    def safe_text(text):
        if use_korean:
            return str(text) if text is not None else ""
        text = str(text) if text is not None else ""
        return re.sub(r'[^\x00-\x7F]+', '', text).strip() or "-"

    pdf.set_font(font_name, "B" if use_korean else "", 16)
    pdf.cell(0, 12, safe_text(title), ln=True, align="C")
    pdf.ln(2)

    pdf.set_font(font_name, size=10)
    pdf.cell(0, 7, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

    conditions = []
    if unit != "선택안함":
        conditions.append(f"Unit={safe_text(unit)}")
    if party != "선택안함":
        conditions.append(f"Party={safe_text(party)}")
    if search:
        conditions.append(f"Search={safe_text(search)}")
    condition_text = "Filter: " + (" / ".join(conditions) if conditions else "None")
    pdf.cell(0, 7, condition_text, ln=True)
    pdf.cell(0, 7, f"Total Records: {len(df)}", ln=True)

    income = df["입금액"].sum()
    expense = df["출금액"].sum()
    net = income - expense
    pdf.cell(0, 7, f"Income: {income:,.0f} KRW", ln=True)
    pdf.cell(0, 7, f"Expense: {expense:,.0f} KRW", ln=True)
    pdf.cell(0, 7, f"Net: {net:,.0f} KRW", ln=True)
    pdf.ln(5)

    pdf.set_font(font_name, "B" if use_korean else "", 8)
    col_widths = [26, 18, 28, 34, 22, 22, 35]
    headers = ["Date", "Unit", "Party", "Desc", "Out", "In", "Memo"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C")
    pdf.ln()

    pdf.set_font(font_name, size=7)
    for _, row in df.iterrows():
        date_str = row["거래일시"].strftime("%Y-%m-%d") if pd.notna(row["거래일시"]) else "-"
        unit_val = safe_text(row["호수"])[:8]
        party_val = safe_text(row["보낸분/받는분"])[:11]
        desc = safe_text(row["적요"])[:13]
        out_amt = f"{row['출금액']:,.0f}" if row["출금액"] > 0 else ""
        in_amt = f"{row['입금액']:,.0f}" if row["입금액"] > 0 else ""
        memo = safe_text(row["송금메모"])[:13]

        pdf.cell(col_widths[0], 7, date_str, border=1)
        pdf.cell(col_widths[1], 7, unit_val, border=1)
        pdf.cell(col_widths[2], 7, party_val, border=1)
        pdf.cell(col_widths[3], 7, desc, border=1)
        pdf.cell(col_widths[4], 7, out_amt, border=1, align="R")
        pdf.cell(col_widths[5], 7, in_amt, border=1, align="R")
        pdf.cell(col_widths[6], 7, memo, border=1)
        pdf.ln()

    output = pdf.output(dest="S")
    if isinstance(output, (bytes, bytearray)):
        return bytes(output)
    else:
        return output.encode("latin-1")

if "df" not in st.session_state:
    st.session_state.df = load_data()

# --------------------------------------------------
# 사이드바
# --------------------------------------------------
with st.sidebar:
    st.title("🏢 로프트프라퍼티스")
    st.caption("임대사업 입출금 관리")
    st.info(f"현재 데이터: **{len(st.session_state.df)}건**")

    st.subheader("1. 엑셀 업로드")
    st.caption("새 거래내역을 추가할 때 사용 (기존 데이터와 합침)")
    uploaded_file = st.file_uploader(
        "거래내역 엑셀 업로드",
        type=["xlsx"],
        key="upload_new",
        help="필수 컬럼: 거래일시, 적요, 보낸분/받는분, 출금액, 입금액, 잔액, 송금메모, 년도"
    )

    if uploaded_file is not None:
        try:
            raw = pd.read_excel(uploaded_file, engine="openpyxl")
            new_df = process_uploaded_df(raw)
            if not st.session_state.df.empty:
                before_count = len(st.session_state.df)
                combined = pd.concat([st.session_state.df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["거래일시", "적요", "보낸분/받는분", "출금액", "입금액"],
                    keep="last"
                )
                st.session_state.df = combined
                added = len(st.session_state.df) - before_count
                st.success(f"업로드 완료! 새로 추가: {added}건 / 전체: {len(st.session_state.df)}건")
            else:
                st.session_state.df = new_df
                st.success(f"업로드 완료! 총 {len(st.session_state.df)}건")
            save_data(st.session_state.df)
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")

    st.divider()

    st.subheader("🔄 수정데이터 업로드")
    st.caption("이전에 받은 수정데이터 백업 파일을 올리면 카테고리·호수 수정 내용이 그대로 반영됩니다.")
    restore_file = st.file_uploader(
        "수정데이터 업로드",
        type=["xlsx"],
        key="upload_restore",
        help="수정데이터_백업_YYYYMMDD.xlsx 파일을 선택하세요"
    )

    if restore_file is not None:
        try:
            raw = pd.read_excel(restore_file, engine="openpyxl")
            restored_df = process_uploaded_df(raw)
            st.session_state.df = restored_df
            save_data(st.session_state.df)
            st.success(f"업로드 완료! 총 {len(st.session_state.df)}건 (카테고리·호수 유지됨)")
            st.rerun()
        except Exception as e:
            st.error(f"업로드 오류: {e}")

    st.divider()

    st.subheader("3. 수동 거래 추가")
    existing_parties = []
    if not st.session_state.df.empty:
        party_df = st.session_state.df[["보낸분/받는분", "호수"]].drop_duplicates()
        party_df["sort_key"] = party_df["호수"].apply(lambda x: 0 if x == "미지정" else 1)
        party_df = party_df.sort_values("sort_key")
        existing_parties = party_df["보낸분/받는분"].dropna().unique().tolist()

    with st.form("add_transaction", clear_on_submit=True):
        add_date = st.date_input("날짜", value=date.today())
        party_option = st.selectbox("상대방 선택 (기존 목록)", ["직접 입력"] + existing_parties)
        if party_option == "직접 입력":
            add_party = st.text_input("상대방 직접 입력")
        else:
            add_party = party_option
        add_unit = st.selectbox("호수", ["선택안함"] + FIXED_UNITS)
        add_type = st.radio("구분", ["입금", "출금"], horizontal=True)
        add_amount = st.number_input("금액", min_value=0, step=1000)
        add_desc = st.text_input("적요")
        add_memo = st.text_input("송금메모")
        add_category = st.selectbox("카테고리", ALL_CATEGORIES)
        submitted = st.form_submit_button("추가하기")

        if submitted:
            if add_amount <= 0:
                st.warning("금액을 입력해주세요.")
            elif not add_party:
                st.warning("상대방을 입력하거나 선택해주세요.")
            else:
                final_unit = add_unit if add_unit != "선택안함" else extract_unit(add_memo)
                new_row = {
                    "거래일시": pd.Timestamp(add_date),
                    "적요": add_desc,
                    "보낸분/받는분": add_party,
                    "출금액": add_amount if add_type == "출금" else 0,
                    "입금액": add_amount if add_type == "입금" else 0,
                    "잔액": None,
                    "송금메모": add_memo,
                    "년도": str(add_date.year),
                    "카테고리": add_category,
                    "호수": final_unit if final_unit else "미지정"
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("거래가 추가되었습니다.")
                st.rerun()

# --------------------------------------------------
# 메인
# --------------------------------------------------
st.title("(주)로프트프라퍼티스 입출금 관리")

if st.session_state.df.empty:
    st.info("왼쪽 사이드바에서 엑셀 파일을 업로드하거나, 수정데이터 업로드로 백업 파일을 올려주세요.")
    st.stop()

today = date.today()
this_month_all = st.session_state.df[
    (st.session_state.df["거래일시"].dt.year == today.year) &
    (st.session_state.df["거래일시"].dt.month == today.month)
]
income_this_month = this_month_all["입금액"].sum()
expense_this_month = this_month_all["출금액"].sum()
net_this_month = income_this_month - expense_this_month

st.subheader("📊 대시보드")
col1, col2, col3 = st.columns(3)
col1.metric("이번 달 입금", f"{income_this_month:,.0f} 원")
col2.metric("이번 달 출금", f"{expense_this_month:,.0f} 원")
col3.metric("이번 달 순현금흐름", f"{net_this_month:,.0f} 원")

# --------------------------------------------------
# 통합 상세 조회
# --------------------------------------------------
st.markdown("#### 🔍 통합 상세 조회 (호수 + 상대방 + 검색어 + 기간)")
st.info("호수, 보낸분/받는분, 검색어, 기간을 모두 합쳐서 해당하는 내역을 전부 보여줍니다. (합집합)")

all_parties = sorted(st.session_state.df["보낸분/받는분"].dropna().unique().tolist()) if not st.session_state.df.empty else []

col_a, col_b = st.columns(2)
with col_a:
    combo_unit = st.selectbox("호수 선택", ["선택안함"] + FIXED_UNITS, key="combo_unit")
with col_b:
    combo_party = st.selectbox("보낸분/받는분 선택", ["선택안함"] + all_parties, key="combo_party")

col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input("시작일", value=None, key="combo_start")
with col_d2:
    end_date = st.date_input("종료일", value=None, key="combo_end")

combo_search = st.text_input(
    "추가 검색어 (여러 개 가능, 공백 또는 / 로 구분)",
    placeholder="예: 계약금 또는 보증금 또는 이혜빈/606호 또는 1,750,000원 등",
    key="combo_search"
)

base_df = st.session_state.df.copy()
masks = []
if combo_unit != "선택안함":
    masks.append(base_df["호수"] == combo_unit)
if combo_party != "선택안함":
    masks.append(base_df["보낸분/받는분"] == combo_party)
if start_date is not None:
    masks.append(base_df["거래일시"] >= pd.Timestamp(start_date))
if end_date is not None:
    masks.append(base_df["거래일시"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
if combo_search:
    keywords = re.split(r'[\s/]+', combo_search.strip())
    keywords = [k for k in keywords if k]
    for kw in keywords:
        kw_clean = kw.replace(",", "").replace("원", "").strip()
        kw_mask = (
            base_df["호수"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["보낸분/받는분"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["적요"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["송금메모"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["출금액"].astype(str).str.contains(kw_clean, case=False, na=False) |
            base_df["입금액"].astype(str).str.contains(kw_clean, case=False, na=False)
        )
        masks.append(kw_mask)

if masks:
    final_mask = masks[0]
    for m in masks[1:]:
        final_mask = final_mask | m
    combo_df = base_df[final_mask].copy()
else:
    combo_df = pd.DataFrame()

if not combo_df.empty:
    c_income = combo_df["입금액"].sum()
    c_expense = combo_df["출금액"].sum()
    c_net = c_income - c_expense

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("조회 건수", f"{len(combo_df)}건")
    c2.metric("입금 합계", f"{c_income:,.0f} 원")
    c3.metric("출금 합계", f"{c_expense:,.0f} 원")
    c4.metric("순현금흐름", f"{c_net:,.0f} 원")

    st.markdown("**조회 결과** (행을 클릭해서 선택하세요)")
    combo_df_display = combo_df[[
        "거래일시", "호수", "보낸분/받는분", "적요", "출금액", "입금액", "송금메모", "카테고리"
    ]].sort_values("거래일시", ascending=False).reset_index(drop=True)

    event = st.dataframe(
        combo_df_display.style.format({"출금액": "{:,.0f}", "입금액": "{:,.0f}"}),
        use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="multi-row", key="combo_select"
    )

    selected_rows = []
    if event and event.selection and event.selection.rows:
        selected_rows = event.selection.rows

    if selected_rows:
        st.write(f"현재 **{len(selected_rows)}건**이 선택되었습니다.")
        if st.button("🗑️ 선택한 내역 삭제", type="primary"):
            try:
                to_delete = combo_df_display.iloc[selected_rows]
                for _, row in to_delete.iterrows():
                    mask = (
                        (st.session_state.df["거래일시"] == row["거래일시"]) &
                        (st.session_state.df["적요"] == row["적요"]) &
                        (st.session_state.df["보낸분/받는분"] == row["보낸분/받는분"]) &
                        (st.session_state.df["출금액"] == row["출금액"]) &
                        (st.session_state.df["입금액"] == row["입금액"])
                    )
                    st.session_state.df = st.session_state.df[~mask]
                save_data(st.session_state.df)
                st.success(f"{len(selected_rows)}건이 삭제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"삭제 중 오류: {e}")
    else:
        st.caption("삭제할 행을 위에서 클릭해서 선택하세요.")

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        try:
            pdf_bytes = create_pdf(combo_df, title="(주)로프트프라퍼티스 입출금 내역",
                                   unit=combo_unit, party=combo_party, search=combo_search)
            st.download_button(
                label="📄 PDF로 다운로드", data=pdf_bytes,
                file_name=f"입출금내역_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.warning(f"PDF 생성 중 오류: {e}")

    with col_dl2:
        try:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                condition_df = pd.DataFrame({
                    "항목": ["호수", "상대방", "검색어", "시작일", "종료일", "조회건수", "입금합계", "출금합계", "순현금흐름"],
                    "내용": [combo_unit, combo_party, combo_search or "-",
                             str(start_date) if start_date else "-", str(end_date) if end_date else "-",
                             len(combo_df), f"{c_income:,.0f}", f"{c_expense:,.0f}", f"{c_net:,.0f}"]
                })
                condition_df.to_excel(writer, index=False, sheet_name="검색조건")
                export_df = combo_df[["거래일시", "호수", "보낸분/받는분", "적요", "출금액", "입금액", "송금메모", "카테고리", "년도"]].sort_values("거래일시", ascending=False)
                export_df.to_excel(writer, index=False, sheet_name="조회결과")
            excel_buffer.seek(0)
            st.download_button(
                label="📊 엑셀로 다운로드", data=excel_buffer,
                file_name=f"입출금내역_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning(f"엑셀 생성 중 오류: {e}")

elif combo_unit == "선택안함" and combo_party == "선택안함" and not combo_search and start_date is None and end_date is None:
    st.caption("호수나 상대방을 선택하거나 검색어/기간을 입력하면 결과가 표시됩니다.")
else:
    st.warning("조건에 맞는 거래 내역이 없습니다.")

# --------------------------------------------------
# 연도별 요약
# --------------------------------------------------
st.markdown("#### 연도별 요약")
yearly = st.session_state.df.groupby("년도").agg(입금합계=("입금액", "sum"), 출금합계=("출금액", "sum")).reset_index()
yearly["순현금흐름"] = yearly["입금합계"] - yearly["출금합계"]
yearly = yearly.sort_values("년도", ascending=False)
st.dataframe(yearly.style.format({"입금합계": "{:,.0f}", "출금합계": "{:,.0f}", "순현금흐름": "{:,.0f}"}), use_container_width=True, hide_index=True)

# --------------------------------------------------
# 최근 6개월
# --------------------------------------------------
st.markdown("#### 최근 6개월 월별 순현금흐름")
df_temp = st.session_state.df.copy()
df_temp["년월"] = df_temp["거래일시"].dt.to_period("M").astype(str)
monthly = df_temp.groupby("년월").agg(입금=("입금액", "sum"), 출금=("출금액", "sum")).reset_index()
monthly["순현금흐름"] = monthly["입금"] - monthly["출금"]
monthly = monthly.sort_values("년월").tail(6)
if not monthly.empty:
    st.bar_chart(monthly.set_index("년월")["순현금흐름"])
else:
    st.info("데이터가 부족합니다.")

st.divider()

# --------------------------------------------------
# 거래 내역
# --------------------------------------------------
st.subheader("📋 거래 내역")

st.success("""
**✏️ 수정 방법 안내**  
• **카테고리** → 더블클릭 후 목록에서 선택  
• **송금메모** → 클릭 후 직접 입력/수정  
• **호수** → 클릭 후 목록에서 선택  
""")

# 필터 (거래기간 바로 위)
st.markdown("##### 필터")
df_all = st.session_state.df.copy()
units = sorted([u for u in df_all["호수"].dropna().unique().tolist() if u != "미지정"]) if not df_all.empty else []
units = ["미지정"] + units if "미지정" in df_all["호수"].values else units
years = sorted(df_all["년도"].dropna().unique().tolist(), reverse=True) if not df_all.empty else []

f1, f2, f3, f4 = st.columns(4)
with f1:
    selected_unit = st.selectbox("호수", ["전체"] + units, key="tx_unit")
with f2:
    selected_year = st.selectbox("연도", ["전체"] + years, key="tx_year")
with f3:
    selected_month = st.selectbox("월", ["전체"] + list(range(1, 13)), key="tx_month")
with f4:
    type_filter = st.radio("구분", ["전체", "입금", "출금"], horizontal=True, key="tx_type")

search_term = st.text_input("검색어 (보낸분/받는분, 적요, 송금메모)", key="tx_search")

st.markdown("##### 거래기간")
col_t1, col_t2 = st.columns(2)
with col_t1:
    tx_start = st.date_input("시작일", value=None, key="tx_start")
with col_t2:
    tx_end = st.date_input("종료일", value=None, key="tx_end")

# 필터 적용
tx_filtered = st.session_state.df.copy()
if selected_unit != "전체":
    tx_filtered = tx_filtered[tx_filtered["호수"] == selected_unit]
if selected_year != "전체":
    tx_filtered = tx_filtered[tx_filtered["년도"] == selected_year]
if selected_month != "전체":
    tx_filtered = tx_filtered[tx_filtered["거래일시"].dt.month == selected_month]
if type_filter == "입금":
    tx_filtered = tx_filtered[tx_filtered["입금액"] > 0]
elif type_filter == "출금":
    tx_filtered = tx_filtered[tx_filtered["출금액"] > 0]
if search_term:
    mask = (
        tx_filtered["보낸분/받는분"].astype(str).str.contains(search_term, case=False, na=False) |
        tx_filtered["적요"].astype(str).str.contains(search_term, case=False, na=False) |
        tx_filtered["송금메모"].astype(str).str.contains(search_term, case=False, na=False)
    )
    tx_filtered = tx_filtered[mask]
if tx_start is not None:
    tx_filtered = tx_filtered[tx_filtered["거래일시"] >= pd.Timestamp(tx_start)]
if tx_end is not None:
    tx_filtered = tx_filtered[tx_filtered["거래일시"] <= pd.Timestamp(tx_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

st.caption(f"현재 표시 건수: **{len(tx_filtered)}건**")

display_df = tx_filtered[[
    "거래일시", "호수", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도", "카테고리"
]].copy().sort_values("거래일시", ascending=False)

edited_df = st.data_editor(
    display_df,
    column_config={
        "거래일시": st.column_config.DatetimeColumn("거래일시", format="YYYY-MM-DD"),
        "호수": st.column_config.SelectboxColumn("호수", options=["미지정"] + FIXED_UNITS, required=True),
        "출금액": st.column_config.NumberColumn("출금액", format="%d"),
        "입금액": st.column_config.NumberColumn("입금액", format="%d"),
        "잔액": st.column_config.NumberColumn("잔액", format="%d"),
        "송금메모": st.column_config.TextColumn("송금메모", help="클릭 후 직접 입력/수정 가능"),
        "카테고리": st.column_config.SelectboxColumn("카테고리", options=ALL_CATEGORIES + ["미분류"], required=True, help="더블클릭 후 선택")
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="transaction_editor"
)

if not edited_df.equals(display_df):
    for idx, row in edited_df.iterrows():
        mask = (
            (st.session_state.df["거래일시"] == row["거래일시"]) &
            (st.session_state.df["적요"] == row["적요"]) &
            (st.session_state.df["보낸분/받는분"] == row["보낸분/받는분"]) &
            (st.session_state.df["출금액"] == row["출금액"]) &
            (st.session_state.df["입금액"] == row["입금액"])
        )
        st.session_state.df.loc[mask, "카테고리"] = row["카테고리"]
        st.session_state.df.loc[mask, "호수"] = row["호수"]
        st.session_state.df.loc[mask, "송금메모"] = row["송금메모"]
    save_data(st.session_state.df)
    st.success("수정 내용이 반영되었습니다. 하단 「수정내용 저장」 버튼을 한 번 더 눌러 주세요.")
    st.rerun()

# 하단 버튼
st.markdown("---")
st.warning("⚠️ 카테고리·호수·송금메모를 수정한 뒤에는 반드시 아래 버튼을 누르세요.")

col_btn1, col_btn2, col_btn3 = st.columns(3)

with col_btn1:
    if st.button("💾 수정내용 저장", type="primary", use_container_width=True):
        save_data(st.session_state.df)
        st.success("수정 내용이 저장되었습니다. 프로그램을 다시 켜도 유지됩니다.")
        st.rerun()

with col_btn2:
    if not tx_filtered.empty:
        tx_buffer = io.BytesIO()
        with pd.ExcelWriter(tx_buffer, engine="openpyxl") as writer:
            export_tx = tx_filtered[[
                "거래일시", "호수", "보낸분/받는분", "적요", "출금액", "입금액", "잔액", "송금메모", "년도", "카테고리"
            ]].sort_values("거래일시", ascending=False)
            export_tx.to_excel(writer, index=False, sheet_name="거래내역")
        tx_buffer.seek(0)
        st.download_button(
            label="📊 엑셀다운로드(현재 필터된 거래내역)",
            data=tx_buffer,
            file_name=f"거래내역_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

with col_btn3:
    if not st.session_state.df.empty:
        full_buffer = io.BytesIO()
        with pd.ExcelWriter(full_buffer, engine="openpyxl") as writer:
            st.session_state.df.to_excel(writer, index=False, sheet_name="전체데이터")
        full_buffer.seek(0)
        st.download_button(
            label="📁 수정데이터 엑셀백업(전체데이터)",
            data=full_buffer,
            file_name=f"수정데이터_백업_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

st.caption("※ 「엑셀다운로드(현재 필터된 거래내역)」= 지금 화면만 / 「수정데이터 엑셀백업(전체데이터)」= 전체 복원용")

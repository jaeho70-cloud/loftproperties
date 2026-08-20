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
SHEET_NAME = "transactions"

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

COLUMNS = ["거래일시", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도", "카테고리", "호수"]

# --------------------------------------------------
# Google 시트 연결
# --------------------------------------------------
def get_gspread_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        return None

def get_worksheet():
    try:
        client = get_gspread_client()
        if client is None:
            return None
        spreadsheet_id = st.secrets["sheets"]["spreadsheet_id"]
        sh = client.open_by_key(spreadsheet_id)
        try:
            ws = sh.worksheet(SHEET_NAME)
        except Exception:
            ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=20)
            ws.append_row(COLUMNS)
        return ws
    except Exception as e:
        st.warning(f"Google 시트 연결 실패: {e}")
        return None

def load_from_sheets():
    ws = get_worksheet()
    if ws is None:
        return None
    try:
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(records)
        for c in COLUMNS:
            if c not in df.columns:
                df[c] = None
        df = df[COLUMNS]
        df["거래일시"] = pd.to_datetime(df["거래일시"], errors="coerce")
        df["출금액"] = pd.to_numeric(df["출금액"], errors="coerce").fillna(0)
        df["입금액"] = pd.to_numeric(df["입금액"], errors="coerce").fillna(0)
        df["잔액"] = pd.to_numeric(df["잔액"], errors="coerce")
        df["년도"] = df["년도"].astype(str)
        df["카테고리"] = df["카테고리"].fillna("미분류").astype(str)
        df["호수"] = df["호수"].fillna("미지정").astype(str)
        return df
    except Exception as e:
        st.warning(f"시트 불러오기 실패: {e}")
        return None

def save_to_sheets(df):
    ws = get_worksheet()
    if ws is None:
        return False
    try:
        export = df.copy()
        export["거래일시"] = export["거래일시"].apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else ""
        )
        export = export.fillna("")
        values = [COLUMNS] + export[COLUMNS].astype(str).values.tolist()
        ws.clear()
        ws.update("A1", values)
        return True
    except Exception as e:
        st.warning(f"시트 저장 실패: {e}")
        return False

# --------------------------------------------------
# 로컬 pickle (보조)
# --------------------------------------------------
def save_data_local(df):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "wb") as f:
            pickle.dump(df, f)
    except Exception:
        pass

def load_data_local():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                return pickle.load(f)
        except:
            pass
    return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    """Google 시트 우선 저장 + 로컬 보조 저장"""
    ok = save_to_sheets(df)
    save_data_local(df)
    return ok

def load_data():
    """Google 시트 우선 로드, 실패 시 로컬"""
    df = load_from_sheets()
    if df is not None:
        return df
    return load_data_local()

# --------------------------------------------------
# 공통 함수
# --------------------------------------------------
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
    pdf.cell(0, 7, "Filter: " + (" / ".join(conditions) if conditions else "None"), ln=True)
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
        pdf.cell(col_widths[0], 7, date_str, border=1)
        pdf.cell(col_widths[1], 7, safe_text(row["호수"])[:8], border=1)
        pdf.cell(col_widths[2], 7, safe_text(row["보낸분/받는분"])[:11], border=1)
        pdf.cell(col_widths[3], 7, safe_text(row["적요"])[:13], border=1)
        pdf.cell(col_widths[4], 7, f"{row['출금액']:,.0f}" if row["출금액"] > 0 else "", border=1, align="R")
        pdf.cell(col_widths[5], 7, f"{row['입금액']:,.0f}" if row["입금액"] > 0 else "", border=1, align="R")
        pdf.cell(col_widths[6], 7, safe_text(row["송금메모"])[:13], border=1)
        pdf.ln()

    output = pdf.output(dest="S")
    return bytes(output) if isinstance(output, (bytes, bytearray)) else output.encode("latin-1")

# --------------------------------------------------
# 세션 초기화
# --------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = load_data()

# --------------------------------------------------
# 사이드바
# --------------------------------------------------
with st.sidebar:
    st.title("🏢 로프트프라퍼티스")
    st.caption("임대사업 입출금 관리")
    st.info(f"현재 데이터: **{len(st.session_state.df)}건**")

    # 시트 연결 상태
    if get_gspread_client() is not None:
        st.success("Google 시트 연결됨")
    else:
        st.warning("Google 시트 미연결 (로컬 저장만 사용)")

    st.subheader("1. 엑셀 업로드")
    st.caption("새 거래내역 추가 (기존과 합침)")
    uploaded_file = st.file_uploader("거래내역 엑셀 업로드", type=["xlsx"], key="upload_new")

    if uploaded_file is not None:
        try:
            raw = pd.read_excel(uploaded_file, engine="openpyxl")
            new_df = process_uploaded_df(raw)
            if not st.session_state.df.empty:
                before = len(st.session_state.df)
                combined = pd.concat([st.session_state.df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["거래일시", "적요", "보낸분/받는분", "출금액", "입금액"], keep="last"
                )
                st.session_state.df = combined
                st.success(f"업로드 완료! +{len(st.session_state.df) - before}건 / 전체 {len(st.session_state.df)}건")
            else:
                st.session_state.df = new_df
                st.success(f"업로드 완료! 총 {len(st.session_state.df)}건")
            save_data(st.session_state.df)
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")

    st.divider()

    st.subheader("🔄 수정데이터 업로드")
    st.caption("백업 엑셀 복원용")
    restore_file = st.file_uploader("수정데이터 업로드", type=["xlsx"], key="upload_restore")
    if restore_file is not None:
        try:
            raw = pd.read_excel(restore_file, engine="openpyxl")
            st.session_state.df = process_uploaded_df(raw)
            save_data(st.session_state.df)
            st.success(f"복원 완료! {len(st.session_state.df)}건")
            st.rerun()
        except Exception as e:
            st.error(f"업로드 오류: {e}")

    st.divider()

    st.subheader("3. 수동 거래 추가")
    existing_parties = []
    if not st.session_state.df.empty:
        party_df = st.session_state.df[["보낸분/받는분", "호수"]].drop_duplicates()
        party_df["sort_key"] = party_df["호수"].apply(lambda x: 0 if x == "미지정" else 1)
        existing_parties = party_df.sort_values("sort_key")["보낸분/받는분"].dropna().unique().tolist()

    with st.form("add_transaction", clear_on_submit=True):
        add_date = st.date_input("날짜", value=date.today())
        party_option = st.selectbox("상대방 선택", ["직접 입력"] + existing_parties)
        add_party = st.text_input("상대방 직접 입력") if party_option == "직접 입력" else party_option
        add_unit = st.selectbox("호수", ["선택안함"] + FIXED_UNITS)
        add_type = st.radio("구분", ["입금", "출금"], horizontal=True)
        add_amount = st.number_input("금액", min_value=0, step=1000)
        add_desc = st.text_input("적요")
        add_memo = st.text_input("송금메모")
        add_category = st.selectbox("카테고리", ALL_CATEGORIES)
        if st.form_submit_button("추가하기"):
            if add_amount <= 0:
                st.warning("금액을 입력해주세요.")
            elif not add_party:
                st.warning("상대방을 입력해주세요.")
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
                st.success("추가되었습니다.")
                st.rerun()

# --------------------------------------------------
# 메인
# --------------------------------------------------
st.title("(주)로프트프라퍼티스 입출금 관리")

if st.session_state.df.empty:
    st.info("사이드바에서 엑셀을 업로드하세요.")
    st.stop()

today = date.today()
this_month = st.session_state.df[
    (st.session_state.df["거래일시"].dt.year == today.year) &
    (st.session_state.df["거래일시"].dt.month == today.month)
]
c1, c2, c3 = st.columns(3)
c1.metric("이번 달 입금", f"{this_month['입금액'].sum():,.0f} 원")
c2.metric("이번 달 출금", f"{this_month['출금액'].sum():,.0f} 원")
c3.metric("이번 달 순현금흐름", f"{(this_month['입금액'].sum() - this_month['출금액'].sum()):,.0f} 원")

# 통합 상세 조회
st.markdown("#### 🔍 통합 상세 조회")
st.info("호수 + 상대방 + 검색어 + 기간 (합집합)")

all_parties = sorted(st.session_state.df["보낸분/받는분"].dropna().unique().tolist())
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
combo_search = st.text_input("추가 검색어", placeholder="예: 계약금 또는 보증금 또는 이혜빈/606호 또는 1,750,000원", key="combo_search")

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
    for kw in [k for k in re.split(r'[\s/]+', combo_search.strip()) if k]:
        kw_clean = kw.replace(",", "").replace("원", "").strip()
        masks.append(
            base_df["호수"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["보낸분/받는분"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["적요"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["송금메모"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["출금액"].astype(str).str.contains(kw_clean, case=False, na=False) |
            base_df["입금액"].astype(str).str.contains(kw_clean, case=False, na=False)
        )

if masks:
    final_mask = masks[0]
    for m in masks[1:]:
        final_mask = final_mask | m
    combo_df = base_df[final_mask].copy()
else:
    combo_df = pd.DataFrame()

if not combo_df.empty:
    ci, ce = combo_df["입금액"].sum(), combo_df["출금액"].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("조회 건수", f"{len(combo_df)}건")
    m2.metric("입금 합계", f"{ci:,.0f} 원")
    m3.metric("출금 합계", f"{ce:,.0f} 원")
    m4.metric("순현금흐름", f"{ci - ce:,.0f} 원")

    combo_df_display = combo_df[["거래일시", "호수", "보낸분/받는분", "적요", "출금액", "입금액", "송금메모", "카테고리"]].sort_values("거래일시", ascending=False).reset_index(drop=True)
    event = st.dataframe(
        combo_df_display.style.format({"출금액": "{:,.0f}", "입금액": "{:,.0f}"}),
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="multi-row", key="combo_select"
    )
    selected_rows = event.selection.rows if event and event.selection and event.selection.rows else []
    if selected_rows:
        st.write(f"**{len(selected_rows)}건** 선택됨")
        if st.button("🗑️ 선택한 내역 삭제", type="primary"):
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
            st.success("삭제되었습니다.")
            st.rerun()
    else:
        st.caption("삭제할 행을 클릭해서 선택하세요.")

    d1, d2 = st.columns(2)
    with d1:
        try:
            st.download_button("📄 PDF로 다운로드", create_pdf(combo_df, unit=combo_unit, party=combo_party, search=combo_search),
                               file_name=f"입출금내역_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf")
        except Exception as e:
            st.warning(f"PDF 오류: {e}")
    with d2:
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                combo_df.sort_values("거래일시", ascending=False).to_excel(writer, index=False, sheet_name="조회결과")
            buf.seek(0)
            st.download_button("📊 엑셀로 다운로드", buf, file_name=f"입출금내역_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.warning(f"엑셀 오류: {e}")
elif combo_unit == "선택안함" and combo_party == "선택안함" and not combo_search and start_date is None and end_date is None:
    st.caption("조건을 입력하면 결과가 표시됩니다.")
else:
    st.warning("조건에 맞는 내역이 없습니다.")

st.markdown("#### 연도별 요약")
yearly = st.session_state.df.groupby("년도").agg(입금합계=("입금액", "sum"), 출금합계=("출금액", "sum")).reset_index()
yearly["순현금흐름"] = yearly["입금합계"] - yearly["출금합계"]
st.dataframe(yearly.sort_values("년도", ascending=False).style.format({"입금합계": "{:,.0f}", "출금합계": "{:,.0f}", "순현금흐름": "{:,.0f}"}), use_container_width=True, hide_index=True)

st.markdown("#### 최근 6개월 월별 순현금흐름")
tmp = st.session_state.df.copy()
tmp["년월"] = tmp["거래일시"].dt.to_period("M").astype(str)
monthly = tmp.groupby("년월").agg(입금=("입금액", "sum"), 출금=("출금액", "sum")).reset_index()
monthly["순현금흐름"] = monthly["입금"] - monthly["출금"]
monthly = monthly.sort_values("년월").tail(6)
if not monthly.empty:
    st.bar_chart(monthly.set_index("년월")["순현금흐름"])

st.divider()

# 거래 내역
st.subheader("📋 거래 내역")
st.success("**✏️ 수정** · 카테고리 더블클릭 선택 · 송금메모/호수 클릭 후 수정")

st.markdown("##### 필터")
df_all = st.session_state.df
units = sorted([u for u in df_all["호수"].dropna().unique() if u != "미지정"])
units = ["미지정"] + units if "미지정" in df_all["호수"].values else units
years = sorted(df_all["년도"].dropna().unique().tolist(), reverse=True)

f1, f2, f3, f4 = st.columns(4)
with f1:
    selected_unit = st.selectbox("호수", ["전체"] + units, key="tx_unit")
with f2:
    selected_year = st.selectbox("연도", ["전체"] + years, key="tx_year")
with f3:
    selected_month = st.selectbox("월", ["전체"] + list(range(1, 13)), key="tx_month")
with f4:
    type_filter = st.radio("구분", ["전체", "입금", "출금"], horizontal=True, key="tx_type")
search_term = st.text_input("검색어", key="tx_search")

st.markdown("##### 거래기간")
t1, t2 = st.columns(2)
with t1:
    tx_start = st.date_input("시작일", value=None, key="tx_start")
with t2:
    tx_end = st.date_input("종료일", value=None, key="tx_end")

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
    tx_filtered = tx_filtered[
        tx_filtered["보낸분/받는분"].astype(str).str.contains(search_term, case=False, na=False) |
        tx_filtered["적요"].astype(str).str.contains(search_term, case=False, na=False) |
        tx_filtered["송금메모"].astype(str).str.contains(search_term, case=False, na=False)
    ]
if tx_start is not None:
    tx_filtered = tx_filtered[tx_filtered["거래일시"] >= pd.Timestamp(tx_start)]
if tx_end is not None:
    tx_filtered = tx_filtered[tx_filtered["거래일시"] <= pd.Timestamp(tx_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

st.caption(f"현재 표시 건수: **{len(tx_filtered)}건**")

display_df = tx_filtered[COLUMNS].sort_values("거래일시", ascending=False)
edited_df = st.data_editor(
    display_df,
    column_config={
        "거래일시": st.column_config.DatetimeColumn("거래일시", format="YYYY-MM-DD"),
        "호수": st.column_config.SelectboxColumn("호수", options=["미지정"] + FIXED_UNITS, required=True),
        "출금액": st.column_config.NumberColumn("출금액", format="%d"),
        "입금액": st.column_config.NumberColumn("입금액", format="%d"),
        "잔액": st.column_config.NumberColumn("잔액", format="%d"),
        "송금메모": st.column_config.TextColumn("송금메모"),
        "카테고리": st.column_config.SelectboxColumn("카테고리", options=ALL_CATEGORIES + ["미분류"], required=True),
    },
    use_container_width=True, hide_index=True, num_rows="fixed", key="transaction_editor"
)

if not edited_df.equals(display_df):
    for _, row in edited_df.iterrows():
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
    st.success("화면 반영됨 → 아래 「수정내용 저장」을 누르세요.")
    st.rerun()

st.markdown("---")
st.warning("⚠️ 카테고리·호수·송금메모를 수정한 뒤에는 반드시 아래 버튼을 누르세요.")

b1, b2, b3 = st.columns(3)
with b1:
    if st.button("💾 수정내용 저장 (Google 시트)", type="primary", use_container_width=True):
        if save_data(st.session_state.df):
            st.success("Google 시트에 저장되었습니다. 다음에 접속해도 유지됩니다.")
        else:
            st.warning("시트 저장 실패. 로컬에만 저장되었을 수 있습니다.")
        st.rerun()
with b2:
    if not tx_filtered.empty:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            tx_filtered[COLUMNS].sort_values("거래일시", ascending=False).to_excel(writer, index=False, sheet_name="거래내역")
        buf.seek(0)
        st.download_button(
            "📊 엑셀다운로드(현재 필터된 거래내역)",
            buf,
            file_name=f"거래내역_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
with b3:
    if not st.session_state.df.empty:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            st.session_state.df.to_excel(writer, index=False, sheet_name="전체데이터")
        buf.seek(0)
        st.download_button(
            "📁 수정데이터 엑셀백업(전체데이터)",
            buf,
            file_name=f"수정데이터_백업_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

st.caption("※ 「수정내용 저장」→ Google 시트에 저장되어 다음날에도 유지됩니다.")

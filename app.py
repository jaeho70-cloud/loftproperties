import streamlit as st
import pandas as pd
from datetime import datetime, date
import re
from fpdf import FPDF
import os
import pickle
import io

# 페이지 설정
st.set_page_config(
    page_title="(주)로프트프라퍼티스 입출금 관리",
    page_icon="🏢",
    layout="wide"
)

# 데이터 저장 경로 (상대 경로 - 로컬/클라우드 공통)
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "transactions.pkl")

# 기본 카테고리 목록
INCOME_CATEGORIES = ["임대수입", "관리비수입", "보증금", "기타수입"]
EXPENSE_CATEGORIES = ["인건비", "세금", "관리용역비", "공과금", "수선유지비", "금융비용", "기타지출"]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

# 고정 호수 목록
FIXED_UNITS = [
    "100호", "101호", "102호", "103호", "104호",
    "201호", "202호", "203호", "204호", "205호", "206호", "207호", "208호",
    "301호", "302호", "303호", "304호",
    "401호", "402호", "403호", "404호", "405호", "406호", "407호", "408호",
    "601호", "602호", "603호", "604호", "605호", "606호", "607호", "608호"
]

# --------------------------------------------------
# 데이터 저장/불러오기 함수
# --------------------------------------------------
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

# --------------------------------------------------
# 호수 추출 함수
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

# --------------------------------------------------
# 카테고리 지정 함수
# --------------------------------------------------
def assign_category(row):
    return "미분류"

# --------------------------------------------------
# PDF 생성 함수
# --------------------------------------------------
def create_pdf(df, title="입출금 내역", unit="선택안함", party="선택안함", search=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    try:
        # 로컬 Windows
        pdf.add_font("Malgun", "", r"C:\Windows\Fonts\malgun.ttf", uni=True)
        pdf.add_font("Malgun", "B", r"C:\Windows\Fonts\malgunbd.ttf", uni=True)
        font_name = "Malgun"
        use_korean = True
    except:
        font_name = "Helvetica"
        use_korean = False

    pdf.set_font(font_name, "B" if use_korean else "", 16)
    pdf.cell(0, 12, title, ln=True, align="C")
    pdf.ln(2)

    pdf.set_font(font_name, size=10)
    pdf.cell(0, 7, f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    
    condition_text = "검색 조건: "
    conditions = []
    if unit != "선택안함":
        conditions.append(f"호수={unit}")
    if party != "선택안함":
        conditions.append(f"상대방={party}")
    if search:
        conditions.append(f"검색어={search}")
    
    if conditions:
        condition_text += " / ".join(conditions)
    else:
        condition_text += "없음"
    
    pdf.cell(0, 7, condition_text, ln=True)
    pdf.cell(0, 7, f"총 건수: {len(df)}건", ln=True)

    income = df["입금액"].sum()
    expense = df["출금액"].sum()
    net = income - expense
    pdf.cell(0, 7, f"입금 합계: {income:,.0f} 원", ln=True)
    pdf.cell(0, 7, f"출금 합계: {expense:,.0f} 원", ln=True)
    pdf.cell(0, 7, f"순현금흐름: {net:,.0f} 원", ln=True)
    pdf.ln(5)

    pdf.set_font(font_name, "B" if use_korean else "", 8)
    col_widths = [26, 18, 28, 34, 22, 22, 35]
    headers = ["날짜", "호수", "상대방", "적요", "출금", "입금", "메모"]

    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C")
    pdf.ln()

    pdf.set_font(font_name, size=7)
    for _, row in df.iterrows():
        date_str = row["거래일시"].strftime("%Y-%m-%d") if pd.notna(row["거래일시"]) else "-"
        unit_val = str(row["호수"])[:8]
        party_val = str(row["보낸분/받는분"])[:11]
        desc = str(row["적요"])[:13]
        out_amt = f"{row['출금액']:,.0f}" if row["출금액"] > 0 else ""
        in_amt = f"{row['입금액']:,.0f}" if row["입금액"] > 0 else ""
        memo = str(row["송금메모"])[:13]

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

# --------------------------------------------------
# 세션 상태 초기화 + 저장된 데이터 불러오기
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

    st.subheader("1. 엑셀 업로드")
    st.caption("새 파일만 올려도 기존 데이터와 자동으로 합쳐집니다.")
    uploaded_file = st.file_uploader(
        "거래내역 엑셀 업로드",
        type=["xlsx"],
        help="필수 컬럼: 거래일시, 적요, 보낸분/받는분, 출금액, 입금액, 잔액, 송금메모, 년도"
    )

    if uploaded_file is not None:
        try:
            new_df = pd.read_excel(uploaded_file, engine="openpyxl")

            required_cols = ["거래일시", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도"]
            missing = [c for c in required_cols if c not in new_df.columns]
            if missing:
                st.error(f"필수 컬럼이 없습니다: {missing}")
            else:
                new_df = new_df[required_cols].copy()
                new_df["거래일시"] = pd.to_datetime(new_df["거래일시"], errors="coerce")
                new_df["출금액"] = pd.to_numeric(new_df["출금액"], errors="coerce").fillna(0)
                new_df["입금액"] = pd.to_numeric(new_df["입금액"], errors="coerce").fillna(0)
                new_df["잔액"] = pd.to_numeric(new_df["잔액"], errors="coerce")
                new_df["년도"] = new_df["년도"].astype(str)

                if "카테고리" not in new_df.columns:
                    new_df["카테고리"] = new_df.apply(assign_category, axis=1)

                new_df["호수"] = new_df["송금메모"].apply(extract_unit)

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

    # 전체 데이터 백업 / 복원
    st.subheader("데이터 백업 / 복원")
    
    if not st.session_state.df.empty:
        # 전체 데이터 엑셀 다운로드
        full_buffer = io.BytesIO()
        with pd.ExcelWriter(full_buffer, engine="openpyxl") as writer:
            st.session_state.df.to_excel(writer, index=False, sheet_name="전체데이터")
        full_buffer.seek(0)
        
        st.download_button(
            label="💾 전체 데이터 엑셀 백업",
            data=full_buffer,
            file_name=f"전체데이터_백업_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.button("⚠️ 데이터 모두 삭제", type="secondary"):
        st.session_state.df = pd.DataFrame(columns=[
            "거래일시", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도", "카테고리", "호수"
        ])
        if os.path.exists(DATA_FILE):
            try:
                os.remove(DATA_FILE)
            except:
                pass
        st.success("데이터가 초기화되었습니다.")
        st.rerun()

    st.divider()

    st.subheader("2. 필터")
    df = st.session_state.df.copy()

    units = sorted([u for u in df["호수"].dropna().unique().tolist() if u != "미지정"]) if not df.empty else []
    units = ["미지정"] + units if "미지정" in df["호수"].values else units
    selected_unit = st.selectbox("호수", ["전체"] + units)

    years = sorted(df["년도"].dropna().unique().tolist(), reverse=True) if not df.empty else []
    selected_year = st.selectbox("연도", ["전체"] + years)

    months = list(range(1, 13))
    selected_month = st.selectbox("월", ["전체"] + months)

    type_filter = st.radio("구분", ["전체", "입금", "출금"], horizontal=True)
    search_term = st.text_input("검색어 (보낸분/받는분, 적요, 송금메모)")

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
        
        party_option = st.selectbox(
            "상대방 선택 (기존 목록)",
            ["직접 입력"] + existing_parties
        )
        
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
                st.session_state.df = pd.concat(
                    [st.session_state.df, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                save_data(st.session_state.df)
                st.success("거래가 추가되었습니다.")
                st.rerun()

# --------------------------------------------------
# 메인 영역
# --------------------------------------------------
st.title("(주)로프트프라퍼티스 입출금 관리")

if st.session_state.df.empty:
    st.info("왼쪽 사이드바에서 엑셀 파일을 업로드하거나 수동으로 거래를 추가해주세요.")
    st.stop()

# 필터 적용
filtered = st.session_state.df.copy()

if selected_unit != "전체":
    filtered = filtered[filtered["호수"] == selected_unit]
if selected_year != "전체":
    filtered = filtered[filtered["년도"] == selected_year]
if selected_month != "전체":
    filtered = filtered[filtered["거래일시"].dt.month == selected_month]
if type_filter == "입금":
    filtered = filtered[filtered["입금액"] > 0]
elif type_filter == "출금":
    filtered = filtered[filtered["출금액"] > 0]
if search_term:
    mask = (
        filtered["보낸분/받는분"].astype(str).str.contains(search_term, case=False, na=False) |
        filtered["적요"].astype(str).str.contains(search_term, case=False, na=False) |
        filtered["송금메모"].astype(str).str.contains(search_term, case=False, na=False)
    )
    filtered = filtered[mask]

# --------------------------------------------------
# 1. 대시보드
# --------------------------------------------------
st.subheader("📊 대시보드")

today = date.today()
this_month = filtered[
    (filtered["거래일시"].dt.year == today.year) &
    (filtered["거래일시"].dt.month == today.month)
]

income_this_month = this_month["입금액"].sum()
expense_this_month = this_month["출금액"].sum()
net_this_month = income_this_month - expense_this_month

col1, col2, col3 = st.columns(3)
col1.metric("이번 달 입금", f"{income_this_month:,.0f} 원")
col2.metric("이번 달 출금", f"{expense_this_month:,.0f} 원")
col3.metric("이번 달 순현금흐름", f"{net_this_month:,.0f} 원")

# --------------------------------------------------
# 2. 통합 상세 조회
# --------------------------------------------------
st.markdown("#### 🔍 통합 상세 조회 (호수 + 상대방 + 검색어)")

st.info("호수, 보낸분/받는분, 추가 검색어를 모두 합쳐서 해당하는 내역을 전부 보여줍니다. (합집합)")

all_parties = sorted(st.session_state.df["보낸분/받는분"].dropna().unique().tolist()) if not st.session_state.df.empty else []

col_a, col_b = st.columns(2)
with col_a:
    combo_unit = st.selectbox("호수 선택", ["선택안함"] + FIXED_UNITS, key="combo_unit")
with col_b:
    combo_party = st.selectbox("보낸분/받는분 선택", ["선택안함"] + all_parties, key="combo_party")

combo_search = st.text_input(
    "추가 검색어 (여러 개 가능, 공백 또는 / 로 구분)",
    placeholder="예: 월세 보증금   또는   이혜빈/606호",
    key="combo_search"
)

base_df = st.session_state.df.copy()
masks = []

if combo_unit != "선택안함":
    masks.append(base_df["호수"] == combo_unit)
if combo_party != "선택안함":
    masks.append(base_df["보낸분/받는분"] == combo_party)
if combo_search:
    keywords = re.split(r'[\s/]+', combo_search.strip())
    keywords = [k for k in keywords if k]
    for kw in keywords:
        kw_mask = (
            base_df["호수"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["보낸분/받는분"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["적요"].astype(str).str.contains(kw, case=False, na=False) |
            base_df["송금메모"].astype(str).str.contains(kw, case=False, na=False)
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
        combo_df_display.style.format({
            "출금액": "{:,.0f}",
            "입금액": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="combo_select"
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

    # 다운로드 버튼 (PDF + 엑셀)
    col_dl1, col_dl2 = st.columns(2)

    with col_dl1:
        try:
            pdf_bytes = create_pdf(
                combo_df, 
                title="(주)로프트프라퍼티스 입출금 내역",
                unit=combo_unit,
                party=combo_party,
                search=combo_search
            )
            st.download_button(
                label="📄 PDF로 다운로드",
                data=pdf_bytes,
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
                    "항목": ["호수", "상대방", "검색어", "조회건수", "입금합계", "출금합계", "순현금흐름"],
                    "내용": [
                        combo_unit,
                        combo_party,
                        combo_search if combo_search else "-",
                        len(combo_df),
                        f"{c_income:,.0f}",
                        f"{c_expense:,.0f}",
                        f"{c_net:,.0f}"
                    ]
                })
                condition_df.to_excel(writer, index=False, sheet_name="검색조건")

                export_df = combo_df[[
                    "거래일시", "호수", "보낸분/받는분", "적요", "출금액", "입금액", "송금메모", "카테고리", "년도"
                ]].copy()
                export_df = export_df.sort_values("거래일시", ascending=False)
                export_df.to_excel(writer, index=False, sheet_name="조회결과")

            excel_buffer.seek(0)

            st.download_button(
                label="📊 엑셀로 다운로드",
                data=excel_buffer,
                file_name=f"입출금내역_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning(f"엑셀 생성 중 오류: {e}")

elif combo_unit == "선택안함" and combo_party == "선택안함" and not combo_search:
    st.caption("호수나 상대방을 선택하거나 검색어를 입력하면 결과가 표시됩니다.")
else:
    st.warning("조건에 맞는 거래 내역이 없습니다.")

# --------------------------------------------------
# 3. 호수별 요약
# --------------------------------------------------
st.markdown("#### 호수별 요약 (현재 필터 기준)")

if not filtered.empty:
    unit_summary = filtered.groupby("호수").agg(
        입금합계=("입금액", "sum"),
        출금합계=("출금액", "sum"),
        건수=("적요", "count")
    ).reset_index()
    unit_summary["순현금흐름"] = unit_summary["입금합계"] - unit_summary["출금합계"]
    unit_summary = unit_summary.sort_values("호수")
    
    st.dataframe(
        unit_summary.style.format({
            "입금합계": "{:,.0f}",
            "출금합계": "{:,.0f}",
            "순현금흐름": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("표시할 데이터가 없습니다.")

# --------------------------------------------------
# 4. 보낸분/받는분별 요약
# --------------------------------------------------
st.markdown("#### 보낸분/받는분별 요약 (현재 필터 기준)")

if not filtered.empty:
    party_summary = filtered.groupby("보낸분/받는분").agg(
        입금합계=("입금액", "sum"),
        출금합계=("출금액", "sum"),
        건수=("적요", "count")
    ).reset_index()
    party_summary["순현금흐름"] = party_summary["입금합계"] - party_summary["출금합계"]
    party_summary = party_summary.sort_values("보낸분/받는분")
    
    st.dataframe(
        party_summary.style.format({
            "입금합계": "{:,.0f}",
            "출금합계": "{:,.0f}",
            "순현금흐름": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

# --------------------------------------------------
# 5. 연도별 요약
# --------------------------------------------------
st.markdown("#### 연도별 요약")
yearly = st.session_state.df.groupby("년도").agg(
    입금합계=("입금액", "sum"),
    출금합계=("출금액", "sum")
).reset_index()
yearly["순현금흐름"] = yearly["입금합계"] - yearly["출금합계"]
yearly = yearly.sort_values("년도", ascending=False)
st.dataframe(
    yearly.style.format({
        "입금합계": "{:,.0f}",
        "출금합계": "{:,.0f}",
        "순현금흐름": "{:,.0f}"
    }),
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# 6. 최근 6개월 순현금흐름
# --------------------------------------------------
st.markdown("#### 최근 6개월 월별 순현금흐름")
df_temp = st.session_state.df.copy()
df_temp["년월"] = df_temp["거래일시"].dt.to_period("M").astype(str)
monthly = df_temp.groupby("년월").agg(
    입금=("입금액", "sum"),
    출금=("출금액", "sum")
).reset_index()
monthly["순현금흐름"] = monthly["입금"] - monthly["출금"]
monthly = monthly.sort_values("년월").tail(6)

if not monthly.empty:
    st.bar_chart(monthly.set_index("년월")["순현금흐름"])
else:
    st.info("데이터가 부족합니다.")

st.divider()

# --------------------------------------------------
# 7. 거래 내역
# --------------------------------------------------
st.subheader(f"📋 거래 내역 ({len(filtered)}건)")

st.info("💡 호수가 '미지정'인 건은 아래에서 직접 수정할 수 있습니다.")

display_df = filtered[[
    "거래일시", "호수", "적요", "보낸분/받는분", "출금액", "입금액", "잔액", "송금메모", "년도", "카테고리"
]].copy()

display_df = display_df.sort_values("거래일시", ascending=False)

edited_df = st.data_editor(
    display_df,
    column_config={
        "거래일시": st.column_config.DatetimeColumn("거래일시", format="YYYY-MM-DD"),
        "호수": st.column_config.SelectboxColumn(
            "호수",
            options=["미지정"] + FIXED_UNITS,
            required=True
        ),
        "출금액": st.column_config.NumberColumn("출금액", format="%d"),
        "입금액": st.column_config.NumberColumn("입금액", format="%d"),
        "잔액": st.column_config.NumberColumn("잔액", format="%d"),
        "카테고리": st.column_config.SelectboxColumn(
            "카테고리",
            options=ALL_CATEGORIES + ["미분류"],
            required=True
        )
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
    save_data(st.session_state.df)
    st.success("호수/카테고리가 업데이트되었습니다.")
    st.rerun()

st.caption("※ Streamlit Cloud에서는 앱이 재시작되면 데이터가 초기질 수 있습니다. 중요한 데이터는 '전체 데이터 엑셀 백업'으로 저장해 두세요.")

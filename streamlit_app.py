
import streamlit as st
import pandas as pd
import fitz
import re
import io
import html
from difflib import SequenceMatcher

st.set_page_config(
    page_title="محلل التقويم المدرسي الذكي",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp {font-family:'Cairo',Tahoma,sans-serif}
.stApp {background:#f7fafb;direction:rtl;color:#143044}
.block-container {max-width:1480px;padding-top:1.4rem;padding-bottom:3rem}
h1,h2,h3,p,label {text-align:right}
h1,h2,h3 {color:#123f4a;letter-spacing:-.4px}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#073c46,#087e86 75%,#0b9e9f);direction:rtl}
[data-testid="stSidebar"] * {color:#fff!important}
[data-testid="stSidebar"] button {border-radius:14px}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {border:1px solid #b9f0ec;border-radius:14px;padding:10px}
.hero {position:relative;overflow:hidden;background:linear-gradient(105deg,#063e49 0%,#076f78 65%,#12a7a6 100%);color:white;padding:35px 36px;border-radius:25px;margin-bottom:25px;box-shadow:0 16px 38px rgba(7,74,81,.13);min-height:175px}
.hero:after {content:"";position:absolute;width:240px;height:240px;border:2px solid #ffffff20;border-radius:50%;top:-130px;left:-50px}
.hero h1 {color:white;text-align:right;font-size:clamp(24px,2.4vw,38px);font-weight:800;margin:0 0 8px}
.hero p {color:#d9f7f5;text-align:right;font-size:15px;margin:3px 0}
.hero .tag {display:inline-block;border:1px solid #ffffff65;background:#ffffff1c;color:white;border-radius:20px;padding:4px 14px;margin-bottom:14px}
.school-photo {width:100%;height:190px;object-fit:cover;border-radius:20px;box-shadow:0 10px 24px #164e6320}
.section-head {border-right:5px solid #10a7a7;padding:8px 16px;background:white;border-radius:12px;margin:18px 0 12px;font-size:21px;font-weight:800;color:#104c59}
[data-testid="stMetric"] {background:white;padding:18px;border-radius:19px;border:1px solid #dcecee;box-shadow:0 5px 22px #174d5810;min-height:125px}
[data-testid="stMetricLabel"] {font-weight:700;color:#45656c}
[data-testid="stMetricValue"] {color:#066e79;font-size:30px;font-weight:800}
div[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:18px}
[data-testid="stFileUploader"] {background:white;border:1px dashed #81c8c9;border-radius:16px;padding:10px}
[data-testid="stDataFrame"] {background:white;border-radius:16px;overflow:hidden;border:1px solid #deebee}
[data-testid="stTabs"] button {font-weight:700}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"] {background:linear-gradient(100deg,#087a82,#0aa4a6);color:white;border:0;border-radius:13px;padding:11px 18px;font-weight:800}
.stButton>button:hover,.stDownloadButton>button:hover {border-color:#0ba5a6}
[data-testid="stAlert"] {border-radius:14px}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🏫 لوحة التحكم")
    st.caption("الابتدائية 111 | 1448هـ")
    st.markdown("### 🖼️ صورة المدرسة")
    photo_upload = st.file_uploader("ارفعي الصورة الأصلية للمدرسة", type=["jpg","jpeg","png"], key="school_photo")
    st.caption("لإظهار الصورة دائمًا، يمكن إضافة ملف school.jpg إلى مستودع GitHub.")
    st.markdown("---")
    st.markdown("**📊 المجالات الأربعة**")
    st.markdown("🏛️ الإدارة المدرسية")
    st.markdown("📚 التعليم والتعلم")
    st.markdown("🎓 نواتج التعلم")
    st.markdown("🛡️ البيئة المدرسية")
    st.markdown("---")
    st.caption("محلل التقويم المدرسي الذكي • إصدار 1448هـ")

st.markdown("""
<div class="hero">
<div class="tag">✦ لوحة المؤشرات الذكية | 1448هـ</div>
<h1>محلل التقويم المدرسي الذكي</h1>
<p>الطفولة المبكرة بالابتدائية الحادية عشرة بعد المائة — ب/111</p>
<p>مقارنة دقيقة بين التقويم الذاتي والخارجي • رسوم بيانية • أولويات التحسين</p>
</div>
""", unsafe_allow_html=True)

if photo_upload is not None:
    st.image(photo_upload, caption="الصورة الأصلية للابتدائية 111", use_container_width=True)
else:
    from pathlib import Path
    if Path("school.jpg").exists():
        st.image("school.jpg", caption="الابتدائية 111", use_container_width=True)

# تحويل الأرقام العربية إلى الإنجليزية
TRANS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬",
    "01234567890123456789.,"
)

def normalize(text):
    text = str(text).translate(TRANS)
    text = text.replace("٪", "%")
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    return text

def normalize_code(code):
    parts = re.findall(r"\d+", normalize(code))
    if len(parts) != 4:
        return None
    # توحيد اتجاه الرمز عند اختلاف ترتيب الاستخراج
    if parts[0] in ("2", "3", "4") and parts[-1] == "1":
        parts = list(reversed(parts))
    return "-".join(parts)

def read_pdf(upload):
    document = fitz.open(stream=upload.getvalue(), filetype="pdf")
    pages = []
    empty_pages = 0
    for index, page in enumerate(document):
        text = normalize(page.get_text(sort=True))
        if len(text.strip()) < 35:
            empty_pages += 1
        pages.append((index + 1, text))
    document.close()
    return pages, empty_pages

CODE_PATTERN = re.compile(
    r"(?<!\d)(?:[1-9]\d?[-–][1-9]\d?[-–][1-9]\d?[-–][1-9]\d?)(?!\d)"
)
PCT_PATTERN = re.compile(
    r"(?:(\d{1,3}(?:\.\d{1,4})?)\s*%|%\s*(\d{1,3}(?:\.\d{1,4})?))"
)

def extract_indicators(pages):
    records = []
    for page_number, page_text in pages:
        lines = [
            re.sub(r"\s+", " ", line).strip()
            for line in page_text.splitlines()
        ]
        lines = [line for line in lines if line]

        # نبحث عن رمز المؤشر ونسبة قريبة منه.
        # نحتفظ بالصفحة والمقتطف للمراجعة البشرية.
        for i, line in enumerate(lines):
            codes = CODE_PATTERN.findall(line)
            if not codes:
                continue

            for raw_code in codes:
                code = normalize_code(raw_code)
                if not code:
                    continue

                nearby = lines[max(0, i-3):min(len(lines), i+9)]
                candidates = []

                for distance, candidate in enumerate(nearby):
                    for match in PCT_PATTERN.finditer(candidate):
                        value = float(match.group(1) or match.group(2))
                        if 0 <= value <= 100:
                            candidates.append(
                                (abs(distance-3), value)
                            )

                value = (
                    sorted(candidates, key=lambda x: x[0])[0][1]
                    if candidates else None
                )

                description = line.replace(raw_code, "").strip()
                if len(description) < 12:
                    description = " ".join(lines[i+1:i+3])[:180]

                records.append({
                    "رمز المؤشر": code,
                    "اسم المؤشر": description,
                    "النسبة": value,
                    "الصفحة": page_number,
                    "مقتطف المصدر": " | ".join(nearby)[:500]
                })

    if not records:
        return pd.DataFrame(columns=[
            "رمز المؤشر", "اسم المؤشر", "النسبة",
            "الصفحة", "مقتطف المصدر"
        ])

    df = pd.DataFrame(records)
    df = df.drop_duplicates(
        subset=["رمز المؤشر", "الصفحة", "النسبة"]
    )
    return df.reset_index(drop=True)

def domain_of(code):
    if not code:
        return "غير محدد"
    first = code.split("-")[0]
    return {
        "1": "الإدارة المدرسية",
        "2": "التعليم والتعلم",
        "3": "نواتج التعلم",
        "4": "البيئة المدرسية"
    }.get(first, "يحتاج مراجعة")

def compare_reports(self_df, external_df):
    # نطابق بالرمز فقط، لا بالتشابه اللفظي وحده.
    # المؤشرات المكررة أو الغامضة تحتاج مراجعة.
    a = self_df.rename(columns={
        "اسم المؤشر": "مؤشر الذاتي",
        "النسبة": "الذاتي %",
        "الصفحة": "صفحة الذاتي",
        "مقتطف المصدر": "شاهد الذاتي"
    })
    b = external_df.rename(columns={
        "اسم المؤشر": "مؤشر الخارجي",
        "النسبة": "الخارجي %",
        "الصفحة": "صفحة الخارجي",
        "مقتطف المصدر": "شاهد الخارجي"
    })

    # منع دمج مضاعف عند تكرار الرمز
    a = a.drop_duplicates("رمز المؤشر", keep="first")
    b = b.drop_duplicates("رمز المؤشر", keep="first")

    merged = pd.merge(
        a, b, on="رمز المؤشر", how="outer",
        indicator=True
    )

    merged["المجال"] = merged["رمز المؤشر"].map(domain_of)
    merged["اسم المؤشر"] = merged[
        "مؤشر الذاتي"
    ].fillna(merged["مؤشر الخارجي"])

    merged["الفرق بالنقاط"] = (
        merged["الذاتي %"] - merged["الخارجي %"]
    )

    def status(row):
        if pd.isna(row["الذاتي %"]) or pd.isna(row["الخارجي %"]):
            return "غير مكتمل"
        d = row["الفرق بالنقاط"]
        if d > 0.25:
            return "ارتفاع"
        if d < -0.25:
            return "انخفاض"
        return "استقرار"

    def analysis(row):
        d = row["الفرق بالنقاط"]
        if pd.isna(d):
            return "استكمال البيانات والتحقق من المصدر"
        if d < -0.25:
            return (
                f"انخفاض {abs(d):.2f} نقطة؛ "
                "تحليل الأسباب ومراجعة الشواهد ووضع إجراء تحسيني"
            )
        if d > 0.25:
            return (
                f"ارتفاع {d:.2f} نقطة؛ "
                "التحقق من أدلة الأداء وقياس الأثر واستدامة الممارسة"
            )
        return "تقارب النتائج؛ متابعة الأداء والمحافظة على المستوى"

    merged["الحالة"] = merged.apply(status, axis=1)
    merged["التحليل والتوصية"] = merged.apply(analysis, axis=1)
    return merged

def excel_file(df, summary):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer, sheet_name="مقارنة المؤشرات", index=False
        )
        summary.to_excel(
            writer, sheet_name="ملخص المجالات", index=False
        )

        for sheet in writer.sheets.values():
            sheet.sheet_view.rightToLeft = True
            sheet.freeze_panes = "A2"
            for column in sheet.columns:
                letter = column[0].column_letter
                max_len = max(
                    len(str(cell.value or ""))
                    for cell in list(column)[:100]
                )
                sheet.column_dimensions[letter].width = min(
                    max(15, max_len + 3), 55
                )
    return output.getvalue()

st.markdown('<div class="section-head">📁 رفع تقريري التقويم المدرسي</div>', unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    self_pdf = st.file_uploader(
        "ارفعي تقرير التقويم الذاتي",
        type=["pdf"], key="self"
    )
with right:
    external_pdf = st.file_uploader(
        "ارفعي تقرير التقويم الخارجي",
        type=["pdf"], key="external"
    )

st.info(
    "يعتمد هذا الإصدار على النص القابل للاستخراج من PDF. "
    "الملفات المصورة ضوئيًا تحتاج إلى OCR قبل المقارنة. "
    "يجب مراجعة الأرقام والمطابقة قبل اعتماد النتائج."
)

if self_pdf and external_pdf:
    if st.button(
        "🔍 استخراج المؤشرات وتحليل التقريرين",
        type="primary",
        use_container_width=True
    ):
        with st.spinner("جاري قراءة التقريرين..."):
            self_pages, self_empty = read_pdf(self_pdf)
            ext_pages, ext_empty = read_pdf(external_pdf)

            self_data = extract_indicators(self_pages)
            ext_data = extract_indicators(ext_pages)

            st.session_state["self_data"] = self_data
            st.session_state["ext_data"] = ext_data
            st.session_state["empty_pages"] = (
                self_empty, ext_empty
            )

if "self_data" in st.session_state:
    self_data = st.session_state["self_data"]
    ext_data = st.session_state["ext_data"]
    empty_self, empty_ext = st.session_state["empty_pages"]

    if empty_self or empty_ext:
        st.warning(
            f"صفحات لا تحتوي على نص كافٍ: "
            f"الذاتي {empty_self}، الخارجي {empty_ext}. "
            "قد تحتاج هذه الصفحات إلى OCR."
        )

    st.subheader("📝 مراجعة البيانات المستخرجة")
    st.caption(
        "راجعي رمز كل مؤشر ونسبته. قد يلتقط الاستخراج "
        "نسبة مؤشر مجاور، خاصة في الجداول متعددة الأعمدة."
    )

    tab1, tab2 = st.tabs([
        "بيانات التقويم الذاتي",
        "بيانات التقويم الخارجي"
    ])

    with tab1:
        edited_self = st.data_editor(
            self_data, num_rows="dynamic",
            use_container_width=True,
            key="edit_self"
        )

    with tab2:
        edited_ext = st.data_editor(
            ext_data, num_rows="dynamic",
            use_container_width=True,
            key="edit_ext"
        )

    # تحديث الرموز بعد تعديلها
    for frame in [edited_self, edited_ext]:
        frame["رمز المؤشر"] = frame["رمز المؤشر"].apply(
            normalize_code
        )
        frame.dropna(
            subset=["رمز المؤشر"], inplace=True
        )
        frame["النسبة"] = pd.to_numeric(
            frame["النسبة"], errors="coerce"
        )
        frame.loc[
            ~frame["النسبة"].between(0, 100),
            "النسبة"
        ] = float("nan")

    comparison = compare_reports(edited_self, edited_ext)

    st.divider()
    st.markdown('<div class="section-head">📊 لوحة مقارنة النتائج</div>', unsafe_allow_html=True)

    matched = comparison["الفرق بالنقاط"].notna()
    improved = (comparison["الحالة"] == "ارتفاع").sum()
    declined = (comparison["الحالة"] == "انخفاض").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي المؤشرات", len(comparison))
    c2.metric("مؤشرات مكتملة", int(matched.sum()))
    c3.metric("مؤشرات ارتفعت", int(improved))
    c4.metric("مؤشرات انخفضت", int(declined))

    domain_summary = (
        comparison.groupby("المجال", as_index=False)
        .agg({
            "الخارجي %": "mean",
            "الذاتي %": "mean",
            "الفرق بالنقاط": "mean"
        })
        .round(2)
    )

    st.markdown('<div class="section-head">📈 مقارنة المجالات الأربعة</div>', unsafe_allow_html=True)
    import plotly.graph_objects as go
    fig = go.Figure()
    for label, color in [("الخارجي %", "#1a5665"), ("الذاتي %", "#17b8b0")]:
        fig.add_trace(go.Bar(
            name=label, x=domain_summary["المجال"],
            y=domain_summary[label], marker_color=color,
            text=domain_summary[label].map(lambda v: f"{v:.1f}%"),
            textposition="outside", textfont=dict(size=14)
        ))
    fig.update_layout(
        barmode="group", template="plotly_white", height=400,
        margin=dict(l=25,r=25,t=40,b=25), font=dict(family="Cairo, Tahoma"),
        legend=dict(orientation="h",y=1.13,x=0.35),
        yaxis=dict(title="النسبة المئوية",range=[0,110]),
        xaxis=dict(title=""),paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "متوسطات المجالات في هذا الرسم محسوبة من المؤشرات "
        "المستخرجة، وليست بالضرورة الدرجات الرسمية للمجالات."
    )

    st.markdown('<div class="section-head">📋 جدول المقارنة والتحليل</div>', unsafe_allow_html=True)

    selected = st.selectbox(
        "اختاري المجال",
        ["جميع المجالات"] +
        sorted(comparison["المجال"].dropna().unique())
    )
    status_filter = st.selectbox(
        "حالة المؤشر",
        ["جميع الحالات", "ارتفاع", "انخفاض",
         "استقرار", "غير مكتمل"]
    )
    search = st.text_input(
        "البحث باسم المؤشر أو رمزه"
    )

    view = comparison.copy()

    if selected != "جميع المجالات":
        view = view[view["المجال"] == selected]

    if status_filter != "جميع الحالات":
        view = view[view["الحالة"] == status_filter]

    if search:
        mask = (
            view["اسم المؤشر"].fillna("").str.contains(
                search, case=False, regex=False
            )
            | view["رمز المؤشر"].fillna("").str.contains(
                search, regex=False
            )
        )
        view = view[mask]

    display_columns = [
        "المجال", "رمز المؤشر", "اسم المؤشر",
        "الخارجي %", "الذاتي %",
        "الفرق بالنقاط", "الحالة",
        "التحليل والتوصية",
        "صفحة الخارجي", "صفحة الذاتي"
    ]

    st.dataframe(
        view[display_columns].round(2),
        use_container_width=True,
        hide_index=True
    )

    st.markdown('<div class="section-head">🎯 أولويات التحسين</div>', unsafe_allow_html=True)

    priorities = comparison[
        comparison["الخارجي %"].notna()
    ].sort_values("الخارجي %").head(10)

    st.dataframe(
        priorities[[
            "المجال", "اسم المؤشر",
            "الخارجي %", "الذاتي %",
            "التحليل والتوصية"
        ]],
        use_container_width=True,
        hide_index=True
    )

    st.warning(
        "اختلاف نتائج التقويم الذاتي والخارجي لا يعني "
        "بالضرورة تحسن الأداء عبر الزمن؛ فقد تختلف "
        "طريقة القياس أو الأدلة أو تاريخ التقييم."
    )

    st.markdown('<div class="section-head">📥 تصدير النتائج</div>', unsafe_allow_html=True)

    excel = excel_file(comparison, domain_summary)

    st.download_button(
        "تحميل ملف Excel الكامل",
        data=excel,
        file_name="تحليل_التقويم_المدرسي_111.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        type="primary"
    )
else:
    st.markdown(
        "### ابدئي برفع التقريرين من الأعلى، ثم اضغطي زر التحليل."
    )

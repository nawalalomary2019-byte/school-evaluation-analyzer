
import io
import re
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import fitz

st.set_page_config(page_title="محلل التقويم المدرسي | ب/111", page_icon="🏫", layout="wide", initial_sidebar_state="expanded")
DOMAINS = ["الإدارة المدرسية", "التعليم والتعلم", "نواتج التعلم", "البيئة المدرسية"]
DOMAIN_ICONS = ["🏛️", "📚", "🎓", "🛡️"]
TRANSLATE = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫", "01234567890123456789.")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'Cairo',Tahoma,sans-serif!important}
.stApp{direction:rtl;background:#f5f9fa;color:#163945}
.block-container{max-width:1480px;padding:1.8rem 2rem 4rem}
h1,h2,h3,p,label{direction:rtl;text-align:right}
h1,h2,h3{color:#103d48}
[data-testid="stSidebar"]{direction:rtl;background:linear-gradient(175deg,#073843,#075f68 55%,#079f9f)}
[data-testid="stSidebar"] *{color:#fff!important}
[data-testid="stSidebar"] [data-testid="stFileUploader"]{background:#ffffff13;border:1px dashed #8ce6df;border-radius:14px}
[data-testid="stMetric"]{background:#fff;border:1px solid #dbe9ea;padding:18px 15px;border-radius:18px;box-shadow:0 8px 25px #0a4e5710}
[data-testid="stMetricValue"]{color:#007f87;font-size:30px;font-weight:800}
[data-testid="stMetricLabel"]{color:#385d64;font-weight:700}
[data-testid="stFileUploader"]{background:#fff;border:1px dashed #71c9c6;border-radius:18px;padding:10px}
[data-testid="stDataFrame"]{border:1px solid #dce9ec;border-radius:16px;overflow:hidden}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:linear-gradient(95deg,#087b85,#0db6b1);color:white;border:0;border-radius:12px;font-weight:800}
.hero{background:linear-gradient(112deg,#063b48,#076a74 58%,#0db5b0);color:white;padding:38px;border-radius:24px;box-shadow:0 14px 35px #0b647022;margin-bottom:25px}
.hero h1{color:white!important;font-size:clamp(27px,3vw,43px);font-weight:800;margin:4px 0 10px}
.hero p{color:#d9f7f4;font-size:16px;margin:4px 0}
.hero .tag{display:inline-block;border:1px solid #ffffff88;background:#ffffff17;padding:5px 15px;border-radius:30px;font-weight:700}
.section{background:white;border-right:6px solid #0ab0aa;border-radius:13px;padding:12px 17px;margin:24px 0 16px;font-size:21px;font-weight:800;color:#0b5561;box-shadow:0 5px 17px #0c485010}
.smallnote{color:#5e7780;font-size:14px}
</style>
""", unsafe_allow_html=True)

def clean(t):
    return str(t).translate(TRANSLATE).replace("٪", "%").replace("–", "-").replace("—", "-")

def norm_code(v):
    v = clean(v)
    m = re.search(r"(?<!\d)([1-4]-\d{1,2}-\d{1,2}-\d{1,2})(?!\d)", v)
    return m.group(1) if m else ""

def domain(code):
    return dict(zip("1234", DOMAINS)).get(str(code)[:1], "غير محدد")

def parse_pdf(file):
    doc = fitz.open(stream=file.getvalue(), filetype="pdf")
    records, weak = [], []
    for n, page in enumerate(doc, 1):
        raw = clean(page.get_text(sort=True))
        if len(raw.strip()) < 60:
            weak.append(n)
        lines = [re.sub(r"\s+", " ", x).strip() for x in raw.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            code = norm_code(line)
            if not code:
                continue
            # Avoid assigning nearby percentages to the wrong indicator.
            # Only accept percentages on the same extracted line.
            values = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%|%\s*(\d{1,3}(?:\.\d+)?)", line)
            vals = [float(a or b) for a,b in values if float(a or b) <= 100]
            if len(vals) != 1:
                continue
            name = re.sub(r"(?<!\d)[1-4]-\d{1,2}-\d{1,2}-\d{1,2}(?!\d)", "", line)
            name = re.sub(r"\d{1,3}(?:\.\d+)?\s*%|%\s*\d{1,3}(?:\.\d+)?", "", name).strip(" -:")
            records.append({"رمز المؤشر":code,"اسم المؤشر":name[:180],"النسبة":vals[0],"الصفحة":n})
    doc.close()
    return pd.DataFrame(records, columns=["رمز المؤشر","اسم المؤشر","النسبة","الصفحة"]), weak

def starter():
    return pd.DataFrame([{"رمز المؤشر":"","اسم المؤشر":"","النسبة":None,"الصفحة":None}])

def tidy(df, source):
    data = df.copy()
    data["رمز المؤشر"] = data["رمز المؤشر"].apply(norm_code)
    data["النسبة"] = pd.to_numeric(data["النسبة"], errors="coerce")
    data = data[data["رمز المؤشر"].ne("") & data["النسبة"].between(0,100)]
    duplicates = data[data["رمز المؤشر"].duplicated(keep=False)]["رمز المؤشر"].unique().tolist()
    data = data[~data["رمز المؤشر"].isin(duplicates)]
    data = data.rename(columns={"اسم المؤشر":"اسم "+source,"النسبة":source+" %","الصفحة":"صفحة "+source})
    return data, duplicates

def compare(a,b):
    a,dup_a=tidy(a,"الذاتي")
    b,dup_b=tidy(b,"الخارجي")
    c=a.merge(b,on="رمز المؤشر",how="outer",validate="one_to_one")
    c["المجال"]=c["رمز المؤشر"].apply(domain)
    c["اسم المؤشر"]=c["اسم الخارجي"].fillna("").where(c["اسم الخارجي"].fillna("").str.len()>8,c["اسم الذاتي"].fillna(""))
    c["الفرق (نقطة)"]=(c["الذاتي %"]-c["الخارجي %"]).round(2)
    c["الحالة"]=c["الفرق (نقطة)"].apply(lambda x:"غير مكتمل" if pd.isna(x) else ("الذاتي أعلى" if x>0.25 else "الخارجي أعلى" if x<-.25 else "متقارب"))
    return c,dup_a,dup_b

def excel_bytes(c,ds):
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        c.to_excel(writer,index=False,sheet_name="المؤشرات")
        ds.to_excel(writer,index=False,sheet_name="المجالات")
        for ws in writer.sheets.values():
            ws.sheet_view.rightToLeft=True
            ws.freeze_panes="A2"
            ws.auto_filter.ref=ws.dimensions
            from openpyxl.styles import Font,PatternFill,Alignment
            for cell in ws[1]:
                cell.fill=PatternFill("solid",fgColor="087C85")
                cell.font=Font(color="FFFFFF",bold=True)
                cell.alignment=Alignment(horizontal="center")
            for col in ws.columns:
                letter=col[0].column_letter
                ws.column_dimensions[letter].width=min(52,max(17,max(len(str(x.value or "")) for x in list(col)[:150])+3))
    return buf.getvalue()

with st.sidebar:
    st.markdown("## 🏫 لوحة التحكم")
    st.caption("الابتدائية الحادية عشرة بعد المائة | 1448هـ")
    photo=st.file_uploader("📷 صورة المدرسة الأصلية",type=["jpg","jpeg","png"],key="photo")
    st.caption("ارفعي الصورة التي أرسلتِها سابقًا. لحفظها دائمًا أضيفيها للمستودع باسم school.jpg.")
    st.divider()
    view=st.radio("🧭 الانتقال السريع",["🏠 الرئيسية","📊 الفرق بين المجالات","📈 الفرق بين المؤشرات","🎯 أولويات التحسين","📥 التصدير"],label_visibility="collapsed")
    st.divider()
    st.caption("النتائج غير المعتمدة لا تُعرض بوصفها نتائج نهائية.")

st.markdown('<div class="hero"><span class="tag">✦ لوحة المؤشرات الذكية | 1448هـ</span><h1>محلل التقويم المدرسي الذكي</h1><p>الطفولة المبكرة بالابتدائية الحادية عشرة بعد المائة — ب/111</p><p>مقارنة التقويم الذاتي والخارجي • مؤشرات الأداء • أولويات التحسين</p></div>',unsafe_allow_html=True)
if photo is not None:
    st.image(photo,caption="الصورة الأصلية لمدرسة ب/111",width=780)
elif Path("school.jpg").exists():
    st.image("school.jpg",caption="مدرسة ب/111",width=780)

st.markdown('<div class="section">📁 تقارير التقويم المدرسي</div>',unsafe_allow_html=True)
x,y=st.columns(2)
with x:
    self_pdf=st.file_uploader("تقرير التقويم الذاتي",type="pdf",key="self_pdf")
with y:
    ext_pdf=st.file_uploader("تقرير التقويم الخارجي",type="pdf",key="ext_pdf")
if st.button("🔍 استخراج البيانات للمراجعة",type="primary",use_container_width=True):
    if not self_pdf or not ext_pdf:
        st.warning("ارفعي التقريرين أولًا.")
    else:
        with st.spinner("قراءة النصوص المتاحة من التقريرين..."):
            a,aw=parse_pdf(self_pdf)
            b,bw=parse_pdf(ext_pdf)
            st.session_state["a"]=a if len(a) else starter()
            st.session_state["b"]=b if len(b) else starter()
            st.session_state["weak"]=(aw,bw)
        st.success("اكتملت محاولة القراءة. راجعي الأرقام أدناه قبل عرض أي مقارنة.")
if "a" not in st.session_state:
    st.info("ارفعي التقريرين، ثم اضغطي استخراج البيانات. يمكن إدخال النسب يدويًا عندما تكون صفحات PDF مصورة.")
    st.stop()

aw,bw=st.session_state["weak"]
if aw or bw:
    st.warning("توجد صفحات تحتاج قراءة ضوئية OCR: الذاتي "+str(aw)+"، الخارجي "+str(bw)+". لن نخمن قيمها. أكملي البيانات من التقرير الأصلي يدويًا.")
st.markdown('<div class="section">✏️ تدقيق بيانات المؤشرات</div>',unsafe_allow_html=True)
st.caption("راجعي رمز المؤشر ونسبته وصفحته. أي مؤشر غير موجود في أحد التقريرين سيظهر غير مكتمل ولن يُحسب له فرق.")
ta,tb=st.tabs(["📘 التقويم الذاتي","📗 التقويم الخارجي"])
with ta:
    a=st.data_editor(st.session_state["a"],num_rows="dynamic",hide_index=True,use_container_width=True,key="edit_a")
with tb:
    b=st.data_editor(st.session_state["b"],num_rows="dynamic",hide_index=True,use_container_width=True,key="edit_b")
c,da,db=compare(a,b)
if da or db:
    st.error("رموز مكررة استُبعدت لحماية دقة النتائج. الذاتي: "+str(da)+" | الخارجي: "+str(db))
complete=c.dropna(subset=["الذاتي %","الخارجي %"])
m1,m2,m3,m4=st.columns(4)
m1.metric("إجمالي الرموز",len(c))
m2.metric("مؤشرات مكتملة",len(complete))
m3.metric("الذاتي أعلى",int((c["الحالة"]=="الذاتي أعلى").sum()))
m4.metric("الخارجي أعلى",int((c["الحالة"]=="الخارجي أعلى").sum()))

if view=="🏠 الرئيسية":
    st.markdown('<div class="section">🏠 ملخص لوحة التحكم</div>',unsafe_allow_html=True)
    st.write("اختاري من القائمة التركوازية: مقارنة المجالات، مقارنة المؤشرات، أولويات التحسين أو التصدير.")
    st.warning("ارتفاع نتيجة الذاتي عن الخارجي هو فرق في التقدير، وليس دليلًا بحد ذاته على تحسن الأداء عبر الزمن.")

if view=="📊 الفرق بين المجالات" or view=="📥 التصدير":
    st.markdown('<div class="section">📊 الفرق بين المجالات الأربعة</div>',unsafe_allow_html=True)
    st.caption("تُدخل درجات المجالات الرسمية من صفحات الملخص في التقريرين. لا نحسبها من متوسطات المؤشرات.")
    rows=[]
    for d,ic in zip(DOMAINS,DOMAIN_ICONS):
        u,v,w=st.columns([2,1,1])
        u.markdown("### "+ic+" "+d)
        sv=v.number_input("الذاتي — "+d,min_value=0.0,max_value=100.0,value=None,step=.25,key="s_"+d)
        ev=w.number_input("الخارجي — "+d,min_value=0.0,max_value=100.0,value=None,step=.25,key="e_"+d)
        rows.append({"المجال":d,"الذاتي %":sv,"الخارجي %":ev,"الفرق (نقطة)":round(sv-ev,2) if sv is not None and ev is not None else None})
    ds=pd.DataFrame(rows)
    valid=ds.dropna(subset=["الذاتي %","الخارجي %"])
    if len(valid):
        fig=go.Figure()
        for col,color in [("الذاتي %","#16b7ae"),("الخارجي %","#165867")]:
            fig.add_bar(x=valid["المجال"],y=valid[col],name=col,marker_color=color,text=valid[col].map(lambda n:f"{n:g}%"),textposition="outside")
        fig.update_layout(barmode="group",template="plotly_white",height=430,font=dict(family="Cairo"),yaxis=dict(range=[0,110],title="النسبة %"),margin=dict(t=35,b=20,l=20,r=20),legend=dict(orientation="h"))
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(ds,use_container_width=True,hide_index=True)
    else:
        st.info("أدخلي القيم الرسمية لإظهار الرسم.")
else:
    ds=pd.DataFrame([{"المجال":d,"الذاتي %":st.session_state.get("s_"+d),"الخارجي %":st.session_state.get("e_"+d)} for d in DOMAINS])
    ds["الفرق (نقطة)"]=ds["الذاتي %"]-ds["الخارجي %"]

if view=="📈 الفرق بين المؤشرات":
    st.markdown('<div class="section">📈 الفرق بين المؤشرات</div>',unsafe_allow_html=True)
    selected=st.selectbox("المجال",["جميع المجالات"]+DOMAINS)
    q=st.text_input("🔎 البحث برمز المؤشر أو اسمه")
    filtered=c if selected=="جميع المجالات" else c[c["المجال"]==selected]
    if q:
        filtered=filtered[filtered["رمز المؤشر"].str.contains(q,regex=False,na=False)|filtered["اسم المؤشر"].str.contains(q,regex=False,na=False)]
    st.dataframe(filtered[["المجال","رمز المؤشر","اسم المؤشر","الذاتي %","الخارجي %","الفرق (نقطة)","الحالة","صفحة الذاتي","صفحة الخارجي"]],hide_index=True,use_container_width=True)
    shown=filtered.dropna(subset=["الفرق (نقطة)"]).sort_values("الفرق (نقطة)")
    if len(shown):
        fig=go.Figure(go.Bar(y=shown["رمز المؤشر"],x=shown["الفرق (نقطة)"],orientation="h",marker_color=["#0baaa7" if v>=0 else "#e19b49" for v in shown["الفرق (نقطة)"]]))
        fig.update_layout(height=max(350,len(shown)*29),template="plotly_white",font=dict(family="Cairo"),xaxis_title="الذاتي ناقص الخارجي (نقطة مئوية)",margin=dict(t=15,b=20))
        st.plotly_chart(fig,use_container_width=True)

if view=="🎯 أولويات التحسين":
    st.markdown('<div class="section">🎯 أولويات التحسين</div>',unsafe_allow_html=True)
    st.caption("الأولوية هنا بحسب انخفاض درجة التقويم الخارجي، لا بحسب الفرق وحده.")
    threshold=st.slider("حد الأولوية: درجة الخارجي أقل من",40,100,80)
    p=c[c["الخارجي %"].notna() & (c["الخارجي %"]<threshold)].sort_values("الخارجي %")
    st.metric("عدد المؤشرات ذات الأولوية",len(p))
    st.dataframe(p[["المجال","رمز المؤشر","اسم المؤشر","الخارجي %","الذاتي %","الفرق (نقطة)"]],hide_index=True,use_container_width=True)
    if len(p):
        fig=go.Figure(go.Bar(y=p["رمز المؤشر"],x=p["الخارجي %"],orientation="h",marker_color="#079b9c",text=p["الخارجي %"]))
        fig.update_layout(height=max(340,len(p)*32),template="plotly_white",xaxis=dict(range=[0,100],title="درجة الخارجي %"),font=dict(family="Cairo"))
        st.plotly_chart(fig,use_container_width=True)
    st.warning("تُعتمد أولويات التحسين النهائية بعد مراجعة شواهد المدرسة وأهمية المؤشر، وليس من النسبة وحدها.")

if view=="📥 التصدير":
    st.markdown('<div class="section">📥 تصدير النتائج</div>',unsafe_allow_html=True)
    st.download_button("📗 تحميل Excel منسق للمجالات والمؤشرات",excel_bytes(c,ds),file_name="تحليل_التقويم_المدرسي_111_1448.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary",use_container_width=True)
    st.caption("يحتوي الملف على القيم المدخلة والمراجعة؛ القيم الناقصة تظل فارغة.")

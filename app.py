import streamlit as st
import pandas as pd
import io

# ====================================================
# 🔒 إعدادات كلمة المرور (قم بتغييرها من هنا)
# ====================================================
PASSWORD = "Nader@992"  # اكتب كلمة المرور التي تريدها هنا

st.set_page_config(page_title="نظام مطابقة مبيعات المنصات و Foodics", layout="wide")

# ====================================================
# 🛡️ نظام التحقق من كلمة المرور
# ====================================================
st.sidebar.title("🔒 تسجيل الدخول")
user_password = st.sidebar.text_input("أدخل كلمة المرور لاستخدام المنصة:", type="password")

if user_password != PASSWORD:
    st.warning("⚠️ يرجى إدخال كلمة المرور الصحيحة في القائمة الجانبية للوصول إلى المنصة.")
    st.info("💡 قم بإدخال كلمة المرور لرؤية أدوات المطابقة وتقارير المبيعات.")
    st.stop()  # يمنع تشغيل باقي الكود إلا بعد إدخال كلمة السر الصحيحة

# ====================================================
# 📊 الكود الرئيسي لنظام المطابقة
# ====================================================
st.title("📊 نظام مطابقة مبيعات منصات التوصيل و Foodics")

# قائمة اختيار المنصة المقابلة لـ Foodics
platform_name = st.sidebar.selectbox(
    "اختر منصة التوصيل المراد مقارنتها مع Foodics:",
    ["Keeta", "Hungerstation", "Jahez", "ToYou", "Ninja", "Chefz", "منصة أخرى"]
)

if platform_name == "منصة أخرى":
    custom_name = st.sidebar.text_input("اكتب اسم المنصة:", value="المنصة")
    platform_name = custom_name if custom_name else "المنصة"

uploaded_file = st.file_uploader(f"اختر ملف الإكسيل لمقارنة (Foodics vs {platform_name})", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # قراءة البيانات
        df = pd.read_excel(uploaded_file)
        df = df.iloc[:, :4]
        df.columns = ['foodics_id', 'foodics_price', 'platform_id', 'platform_price']

        # تنظيف أرقام الطلبات والأسعار
        df['foodics_id'] = df['foodics_id'].astype(str).str.strip().str.replace('.0', '', regex=False)
        df['platform_id'] = df['platform_id'].astype(str).str.strip().str.replace('.0', '', regex=False)
        
        df['foodics_price'] = pd.to_numeric(df['foodics_price'], errors='coerce').fillna(0)
        df['platform_price'] = pd.to_numeric(df['platform_price'], errors='coerce').fillna(0)

        # دمج البيانات
        f_df = df[['foodics_id', 'foodics_price']].dropna(subset=['foodics_id'])
        p_df = df[['platform_id', 'platform_price']].dropna(subset=['platform_id'])

        merged = pd.merge(
            p_df, 
            f_df, 
            left_on='platform_id', 
            right_on='foodics_id', 
            how='outer'
        )

        merged['platform_price'] = merged['platform_price'].fillna(0)
        merged['foodics_price'] = merged['foodics_price'].fillna(0)

        # توحيد رقم الطلب والفرق
        merged['order_id'] = merged['platform_id'].combine_first(merged['foodics_id'])
        merged['diff'] = (merged['platform_price'] - merged['foodics_price']).round(2)

        # تحديد نوع التباين ديناميكياً حسب اسم المنصة
        def classify_variance(row):
            d = row['diff']
            if pd.isna(row['foodics_id']) or row['foodics_id'] == 'nan':
                return 'طلب غير مسجل بفودكس'
            elif pd.isna(row['platform_id']) or row['platform_id'] == 'nan':
                return f'طلب غير مسجل بـ {platform_name}'
            elif d == 0:
                return 'مطابق'
            elif d == 12.0:
                return 'رسوم توصيل غير مسجلة بفودكس'
            elif d == 24.0:
                return 'رسوم توصيل مضاعفة'
            elif d > 0:
                return f'زيادة في {platform_name} (+{d:.2f})'
            else:
                return f'نقص في {platform_name} ({d:.2f})'

        merged['variance_type'] = merged.apply(classify_variance, axis=1)

        # --- الحسابات المالية العامة ---
        total_orders = len(merged)
        matched_df = merged[merged['variance_type'] == 'مطابق']
        diff_df = merged[merged['variance_type'] != 'مطابق'].copy()

        matched_count = len(matched_df)
        diff_count = len(diff_df)

        total_platform = merged['platform_price'].sum()
        total_foodics = merged['foodics_price'].sum()
        net_diff = total_platform - total_foodics
        note_diff = f"فروقات لصالح {platform_name}" if net_diff >= 0 else "فروقات لصالح فودكس"

        # ==========================================
        # 1. تقرير مطابقة مبيعات Foodics و المنصة
        # ==========================================
        st.subheader(f"تقرير مطابقة مبيعات {platform_name} و Foodics")
        
        summary_df = pd.DataFrame({
            "المؤشر / البيان": [
                "إجمالي عدد الطلبات",
                "طلبات مطابقة تماماً",
                "طلبات بها فروقات في القيمة",
                f"إجمالي مبيعات {platform_name} (ريال)",
                "إجمالي مبيعات Foodics (ريال)",
                f"صافي الفروقات (زيادة {platform_name})"
            ],
            "القيمة / العدد": [
                f"{total_orders:,}",
                f"{matched_count:,}",
                f"{diff_count:,}",
                f"{total_platform:,.2f}",
                f"{total_foodics:,.2f}",
                f"{abs(net_diff):,.2f}"
            ],
            "النسبة / الملاحظة": [
                "100%",
                f"{(matched_count/total_orders*100):.2f}%" if total_orders > 0 else "0%",
                f"{(diff_count/total_orders*100):.2f}%" if total_orders > 0 else "0%",
                f"حسب تقارير {platform_name}",
                "حسب تقارير فودكس",
                note_diff
            ]
        })
        st.table(summary_df)

        st.markdown("---")

        # ==========================================
        # 2. تحليل نوعية الفروقات
        # ==========================================
        st.subheader("تحليل نوعية الفروقات")
        if not diff_df.empty:
            breakdown = diff_df.groupby('diff').agg(
                عدد_الطلبات=('order_id', 'count'),
                إجمالي_الفرق=('diff', 'sum')
            ).reset_index()

            breakdown['نوع الفرق (ريال)'] = breakdown['diff'].apply(
                lambda x: f"+{x:.2f} ريال" if x > 0 else f"{x:.2f} ريال"
            )
            
            breakdown_display = breakdown[['نوع الفرق (ريال)', 'عدد_الطلبات', 'إجمالي_الفرق']]
            breakdown_display.columns = ['نوع الفرق (ريال)', 'عدد الطلبات', 'إجمالي الفرق (ريال)']
            breakdown_display['إجمالي الفرق (ريال)'] = breakdown_display['إجمالي الفرق (ريال)'].apply(lambda x: f"{x:,.2f}")
            
            st.table(breakdown_display)

            st.markdown("---")

            # ==========================================
            # 3. قائمة الطلبات ذات الفروقات المالية
            # ==========================================
            st.subheader(f"قائمة الطلبات ذات الفروقات المالية ({diff_count} طلباً)")

            diff_df_display = diff_df.reset_index(drop=True)
            diff_df_display['م'] = diff_df_display.index + 1

            report_table = diff_df_display[[
                'م', 
                'order_id', 
                'platform_price', 
                'foodics_price', 
                'diff', 
                'variance_type'
            ]]

            report_table.columns = [
                'م', 
                'رقم الطلب (Order ID)', 
                f'قيمة {platform_name} (ريال)', 
                'قيمة Foodics (ريال)', 
                f'الفرق ({platform_name} - Foodics)', 
                'نوع التباين'
            ]

            st.dataframe(report_table, use_container_width=True)

            # --- تصدير ملف Excel الشامل ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='الملخص التنفيذي', index=False)
                breakdown_display.to_excel(writer, sheet_name='تحليل الفروقات', index=False)
                report_table.to_excel(writer, sheet_name='تفاصيل الفروقات', index=False)

            st.download_button(
                label=f"📥 تحميل تقرير مطابقة {platform_name} الشامل (Excel)",
                data=buffer.getvalue(),
                file_name=f'تقرير_مطابقة_مبيعات_{platform_name}_و_Foodics.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.success(f"🎉 جميع البيانات مطابقة 100%! لا يوجد أي فروقات بين Foodics و {platform_name}.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة الملف: {e}")
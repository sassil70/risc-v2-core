---
pdf_options:
  format: A4
  margin: 15mm
  printBackground: true
---
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&family=Inter:wght@400;600&display=swap');

body { 
    font-family: 'Inter', 'Tajawal', sans-serif; 
    line-height: 1.6;
    color: #333;
}
h1 { color: #1a365d; text-align: center; border-bottom: 2px solid #ebf8ff; padding-bottom: 10px; }
h2 { color: #2b6cb0; margin-top: 30px; }
h3 { color: #2c5282; }
.hero-img { width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 20px 0; }
.note { background-color: #ebf8ff; padding: 15px; border-left: 5px solid #3182ce; border-radius: 4px; margin: 15px 0;}
.ar-text { direction: rtl; text-align: right; font-family: 'Tajawal', sans-serif; }
.page-break { page-break-before: always; }
</style>

# RISC V2: Expert Surveyor Beta Testing Guide

<div style="text-align: center; margin-bottom: 20px; color: #718096;">
  <em>Confidential Beta - Bilingual Document (English / Arabic)</em>
</div>

![Dashboard Overview](/Users/SalimBAssil/.gemini/antigravity/brain/5a74c755-1f23-489d-b791-c29eebf9ac0a/dashboard_view_1775017978148.png)

## 🌟 Welcome to the Future of Surveying

**Dear Expert Surveyors,**

You hold years of unparalleled field experience that no software can replicate. That is precisely why we built **RISC V2**. We did not build this system to change how you work; we built it to remove the friction from your work. You are invited to this exclusive Beta test to help us mold it. We need your sharp eyes, your deep RICS-standard knowledge, and your honest critique.

---

## 🏛️ System Architecture Workflow

Our system is composed of three main pillars working in perfect harmony in the Cloud.

```mermaid
graph LR
    A[📱 The Witness App<br>Field Data Collection] -->|Syncs Instantly| B(🤖 The Brain Cluster<br>Gemini AI Processing)
    B --> C{Decision Matrix}
    C -->|Drafting| D[📝 Text Refinement]
    C -->|Tags| E[🏷️ Defect Categorization]
    D --> F[📊 Management Dashboard<br>Review & Polish]
    E --> F
    F -->|Export| G(📄 Final RICS PDF Report)
    style A fill:#e6f6ff,stroke:#3182ce,stroke-width:2px
    style B fill:#fff5f5,stroke:#e53e3e,stroke-width:2px
    style G fill:#f0fff4,stroke:#38a169,stroke-width:2px
```

<div class="note">
<strong>Your Field Mission (Testing Phase):</strong> Try to break the app! Take photos of complex structures, record voice dictations speaking naturally about defects, and watch the AI instantly format your raw thoughts into professional architectural paragraphs.
</div>

---

## 🐛 Bug Reporting & Feedback Protocol

When you find a glitch or have a brilliant idea to save time on-site, report it to our WhatsApp group:

1. **Device:** (e.g., iPhone 15 Pro, Samsung S24)
2. **Location:** (e.g., Image Gallery screen)
3. **Issue/Idea:** (e.g., "App froze when taking 5 rapid pictures" OR "It would save me 2 hours if the camera auto-tagged dampness.")
4. **Visuals:** Always attach a **Screenshot**!

<div class="page-break"></div>

<div class="ar-text">

# نظام RISC V2: الدليل الإرشادي للخبراء (نسخة البيتا)

![Report Preview](/Users/SalimBAssil/.gemini/antigravity/brain/5a74c755-1f23-489d-b791-c29eebf9ac0a/html_report_view_1775018020963.png)

## 🌟 مرحباً بكم في مستقبل المسح الهندسي

**خبراءنا وزملاءنا المهندسون،**

أنتم تمتلكون سنوات من الخبرة الميدانية العميقة التي لا يمكن لأي آلة برمجية محاكاتها. ولهذا السبب تحديداً قمنا ببناء هذا النظام **RISC V2**. نحن لم نصمم هذا البرنامج لتغيير مبادئ عملكم الراسخة، بل برمجناه لإزالة العقبات الروتينية والورقية من طريقكم.

لقد دعوناكم لهذه النسخة التجريبية (Beta) ليس لمجرد "تجربة تطبيق تقني"، بل لتكونوا شركاءنا المهندسين في صياغته. نحن بحاجة إلى أعينكم الثاقبة، ومعرفتكم العميقة بمعايير RICS الهندسية، ونقدكم البنّاء لنجعل من هذا النظام السلاح الأقوى في مجال الفحص.

---

## 🏛️ مخطط واجهات العمل (User Experience Flow)

كيف تتحرك بياناتكم من أرض الموقع إلى التقرير المطبوع؟

```mermaid
journey
    title مسار تدفق البيانات (من الميدان إلى التقرير)
    section ١. العمل الميداني
      التقاط الصور (شاشة الكاميرا): 5: المساح
      التسجيل الصوتي للملاحظات: 4: المساح
    section ٢. الذكاء الاصطناعي السحابي
      تحليل الأضرار الإنشائية: 5: النظام الذكي
      صياغة الفقرات الهندسية: 4: النظام الذكي
    section ٣. لوحة الإدارة النهائية
      مراجعة المخرجات وتعديلها: 5: مدير المشروع
      إصدار تقرير RICS النهائي: 5: النظام
```

<div class="note">
<strong>ما المطلوب منكم؟ (مهمة التجربة):</strong> نريد منكم استخدام النظام وكأنكم في فحص موقع حقيقي.. لا تترددوا في اختباره بقسوة وأثناء حركة سريعة! انتقلوا بين الغرف، العبوا بالصور، وتحدثوا بشكل طبيعي للبرنامج عن المشاكل (مثلاً: "وجود رطوبة صعودية شديدة أسفل الجدار"). ولاحظوا كيف سيحوّلها النظام لفقرات هندسية معتمدة.
</div>

---

## 🐛 كيفية التبليغ وتقييم البرنامج (مجموعة الواتساب)

المشاكل البرمجية سهلة الإصلاح، ولكن توجيهكم المهني هو الأهم. في حال واجهتكم مشكلة أو خطرت لكم فكرة، نرجو الإرسال للجروب بالصيغة التالية:

1. **نوع الهاتف:** (آيفون أو أندرويد)
2. **مكان المشكلة:** (مثال: شاشة رفع الصور)
3. **الفكرة/المشكلة:** (مثال: الشاشة علقت فجأة - أو - لدي فكرة لوضع تصنيف تلقائي للرطوبة سيوفر علينا ساعتين من العمل).
4. **صورة للشاشة:** لقطة شاشة (Screenshot) تخبرنا بألف كلمة!

</div>

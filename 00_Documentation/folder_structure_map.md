# 📂 خريطة المجلدات (Folder Structure Map)
**المشروع:** RISC V2.0 Core System
**المسار الجذري:** `RISC_V2_Core_System/`

---

## 🏗️ الهيكل العام (The Big Picture)
النظام مقسم إلى 4 كتل وظيفية (Clusters) ومجلد توثيق، لضمان استقلالية التطوير (Decoupled Development).

```text
RISC_V2_Core_System/
├── 00_Documentation/       # 🧠 الذاكرة (Maps, Schemas, Contracts)
├── 01_Witness_Cluster/     # 👁️ الشاهد (Mobile App Source)
├── 02_Brain_Cluster/       # 💽 الدماغ (Backend, DB, Sync)
├── 03_Reporter_Cluster/    # 🤖 المحلل (AI Logic)
└── 04_Management_Cluster/  # 👔 الإدارة (Web Dashboard)
```

---

## تفاصيل المجلدات (Deep Dive)

### 📂 `00_Documentation/`
*كل ما هو ليس كوداً.*
*   يحتوي على مخططات Mermaid، ملفات Markdown، وقواميس البيانات.
*   **القاعدة:** أي تغيير في الكود يجب أن يسبقه تحديث لملف هنا.

### 📂 `01_Witness_Cluster/`
*تطبيق الموبايل (Flutter).*
*   يحتوي على كود `lib/`، `pubspec.yaml`، واختبارات `test/`.
*   الهدف: إنتاج ملف `.apk` يعمل دون إنترنت.

### 📂 `02_Brain_Cluster/`
*الخادم المركزي.*
*   يحتوي على `Dockerfile` الخاص بـ AlloyDB Omni.
*   يحتوي على كود Python FastAPI للمزامنة (`/sync`).
*   يحتوي على `migrations/` لبنية قاعدة البيانات.

### 📂 `03_Reporter_Cluster/`
*محرك الذكاء.*
*   يحتوي على سكريبتات Python التي تتحدث مع Gemini API.
*   لا يحتوي على قاعدة بيانات، بل يقرأ من `02_Brain_Cluster`.

### 📂 `04_Management_Cluster/`
*واجهة الويب.*
*   يحتوي على كود Frontend (Web) للمدراء.
*   مسؤول عن عرض الـ PDF النهائي.

---

## 🔒 ملاحظات Git
*   يتم تجاهل ملفات `.env` و `build/` في كل كتلة عبر `.gitignore` جذري.
*   نحافظ على هذا الهيكل نظيفاً ولا نضيف مجلدات عشوائية (مثل `temp` أو `test_v1`) في الجذر.

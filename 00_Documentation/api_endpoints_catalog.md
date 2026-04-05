# 🔌 كتالوج واجهات الاتصال (API Endpoints Catalog)
**المعيار:** RESTful via FastAPI
**التوقيت:** صارم جداً (ISO 8601 UTC).

---

## 🌍 معيار الزمن العالمي (Time Zone Standard)
*   **المشكلة:** لدينا مستخدمون في 4 مناطق زمنية مختلفة (لندن، دبي، الرياض، القاهرة).
*   **الحل:** السيرفر **أعمى زمنياً**. هو لا يعرف "صباحاً" أو "مساءً".
    *   **الموبايل:** يحول وقت الالتقاط المحلي (مثلاً 14:00 بتوقيت مكة) إلى UTC (أي 11:00Z) قبل الإرسال.
    *   **قاعدة البيانات:** تخزن `timestamp with time zone` بقيمة UTC حصراً.
    *   **العرض:** واجهة الويب فقط هي من تقوم بتحويل UTC إلى توقيت "موقع العقار" عند الطباعة.

---

## 1. بوابة المزامنة (Sync Cluster APIs)
*المسار الأساسي: `/api/v2/sync`*

### `POST /handshake` (المصافحة)
*   **الوصف:** يبدأ جلسة رفع البيانات.
*   **Request:**
    ```json
    {
      "session_id": "uuid",
      "package_hash": "sha256_string",
      "package_size_bytes": 10485760,
      "device_timestamp_utc": "2026-01-06T15:30:00Z" // للمقارنة وكشف التلاعب بالساعة
    }
    ```
*   **Response:**
    *   `200 OK`: الحزمة موجودة، لا ترسل.
    *   `201 Created`: ابدأ الرفع.
    *   `409 Conflict`: ساعة الجهاز غير مضبوطة (فارق > 5 دقائق).

### `POST /upload` (الرفع)
*   **الوصف:** يستقبل البيانات الثنائية (Binary Stream).
*   **Headers:** `Content-Type: application/octet-stream`.

### `POST /commit` (التثبيت)
*   **الوصف:** يخبر السيرفر "انتهيت من الرفع، تحقق من الهاش الآن".
*   **Response:** `200 OK` (Integrity Verified) أو `400 Bad Request` (Corrupted).

---

## 2. بوابة الذكاء (Reporter Cluster APIs)
*المسار الأساسي: `/api/v2/ai`*

### `POST /analyze/room`
*   **الوصف:** يطلب من جيميناي تحليل غرفة بناءً على البيانات التي تمت مزامنتها.
*   **Request:** `{"room_id": "uuid", "force_reanalysis": false}`
*   **Note:** لا نرسل صوراً هنا. الصور موجودة بالفعل في `AlloyDB`. نرسل فقط المعرف (ID).

### `GET /report/{project_id}/status`
*   **الوصف:** يعرض نسبة اكتمال التقرير (مثلاً: "جاري تحليل المطبخ... 40%").
*   **Response:**
    ```json
    {
      "status": "processing",
      "current_stage": "Living Room",
      "progress_percent": 45,
      "estimated_remaining_seconds": 120
    }
    ```

---

## 3. بوابة الإدارة (Management Cluster APIs)
*المسار الأساسي: `/api/v2/manage`*

### `GET /projects/{id}/pdf`
*   **الوصف:** يولد رابط تحميل التقرير النهائي.
*   **Query Params:** `?timezone=Asia/Riyadh` (هنا فقط نحدد الزمن للعرض).

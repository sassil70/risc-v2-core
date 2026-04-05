# 🗄️ مخطط قاعدة البيانات (Database Schema ERD)
**المحرك:** Google AlloyDB Omni (PostgreSQL Compatible)
**المميزات المفعلة:** `pgvector` (للمتجهات), `Columnar Engine` (للتحليل السريع).

---

## 🏗️ المخطط البياني (ERD)

```mermaid
erDiagram
    PROJECTS ||--|{ SESSIONS : "contains"
    SESSIONS ||--|{ MEDIA_ASSETS : "captures"
    SESSIONS ||--|{ ROOMS : "defines"
    ROOMS ||--|{ RICS_ITEMS : "contains"
    
    MEDIA_ASSETS ||--o| AI_EMBEDDINGS : "has_vector"
    MEDIA_ASSETS ||--o| ANNOTATIONS : "has_findings"

    %% Forensic Layer
    PROJECTS ||--o{ IMMUTABLE_AUDIT_LOG : "tracked_by"
    SESSIONS ||--o{ IMMUTABLE_AUDIT_LOG : "tracked_by"

    %% Sync Layer
    DEVICES ||--|{ SYNC_STATE : "syncs_with"

    PROJECTS {
        uuid id PK
        string reference_number
        string client_name
        jsonb site_metadata "ZenRows Data"
        timestamp created_at
    }

    SESSIONS {
        uuid id PK
        uuid project_id FK
        uuid device_id FK
        timestamp started_at
        timestamp closed_at
        boolean is_locked "Witness Seal"
    }

    MEDIA_ASSETS {
        uuid id PK
        uuid session_id FK
        string file_path "Local/S3"
        string file_hash "SHA-256"
        timestamp captured_at
        jsonb sensor_data "GPS, LiDAR"
    }

    AI_EMBEDDINGS {
        uuid asset_id FK
        vector embedding_vector "Dimensions: 768"
        string model_version "Gemini 3.0"
    }

    IMMUTABLE_AUDIT_LOG {
        bigint id PK
        string table_name
        uuid record_id
        string operation "INSERT/UPDATE/DELETE"
        jsonb old_value
        jsonb new_value
        timestamp changed_at
        string changed_by_user
    }
```

---

## 🔍 تفاصيل الجداول التقنية

### 1. `immutable_audit_log` (الصندوق الأسود)
*   **الوظيفة:** جدول لا يكتب فيه التطبيق أبداً. يتم ملؤه فقط بواسطة **Triggers** داخل قاعدة البيانات.
*   **الهدف الجنائي:** إذا حاول أي مبرمج أو مخترق تغيير "تاريخ التقاط الصورة" في جدول `MEDIA_ASSETS`، سيقوم التريجر فوراً بتسجيل النسخة القديمة والجديدة ووقت التغيير هنا. هذا الجدول هو "الدليل القاطع" أمام المحكمة.

### 2. `ai_embeddings` (الذاكرة البصرية)
*   **الوظيفة:** تخزين ناتج تحليل Gemini للصورة كـ "مصفوفة أرقام" (Vector).
*   **الفائدة:** يسمح لنا بالبحث الدلالي. مثال: *"أعطني كل الصور التي تحتوي على عفن أسود في الزوايا"*، حتى لو لم نكتب ذلك في الوصف النصي. يتم استخدام إضافة `pgvector`.

### 3. `site_metadata` (الذكاء المسبق)
*   **نوع البيانات:** `JSONB`.
*   **الوظيفة:** تخزين البيانات القادمة من **ZenRows** (نوع التربة، خطر الفيضان، الصور التاريخية) بشكل مرن (NoSQL style) داخل جدول المشاريع، مما يسهل استدعاءها عند توليد التقرير.

### 4. `sync_queue` (المصافحة)
*   **الوظيفة:** جدول مؤقت لتنظيم وصول البيانات من الموبايل.
*   **الآلية:** لا يتم دمج البيانات في `MEDIA_ASSETS` إلا بعد التأكد من سلامة "الهاش" (Hash Integrity).

---

## 🔒 ملاحظة أمان
كلمة مرور المستخدمين **لا تخزن هنا**. نستخدم Google Identity Platform أو Firebase Auth، ونخزن فقط `user_uid` للربط.

import os
import zipfile
import webbrowser
import urllib.parse

def create_zip_package():
    vault_dir = "/Users/SalimBAssil/Documents/AntiGravity_Core_Vault_v2026/04_Source_Code/RISC_V2_Core_System"
    output_path = os.path.join(vault_dir, "RISC_Witness_V2_OfflineDemo_Update.zip")
    
    files_to_zip = [
        "01_Witness_Cluster/lib/core/services/auth_service.dart",
        "02_Brain_Cluster/routers/auth.py",
        "02_Brain_Cluster/main.py"
    ]
    
    print(f"📦 Creating Update Package at {output_path}...")
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for file in files_to_zip:
            full_path = os.path.join(vault_dir, file)
            if os.path.exists(full_path):
                zipf.write(full_path, arcname=file)
                print(f"  ✅ Added: {file}")
            else:
                print(f"  ❌ Missing: {file}")
                
    return output_path

def draft_email(zip_path):
    print("📧 Drafting Email to Eng. Ahmed El Hamshary...")
    subject = "عاجل: تحديث تطبيق RISC V2 Witness - تجاوز مراجعة Apple (بند 2.1a)"
    body = """تحياتي مهندس أحمد،

تم الانتهاء من حل مشكلة الرفض من أبل (بند 2.1a).
لقد قمت ببرمجة دمج وضع "عرض توضيحي محلي" (Demo Fallback) داخل التطبيق نفسه. 
هذا يعني أن مراجعي أبل سيتمكنون الآن من تسجيل الدخول باستخدام الحساب: 
Username: demo
Password: demo1234
حتى لو كانت السيرفرات السحابية مغلقة أو قيد التحديث.

أرجو منك:
1. بناء ملف الـ Archive عبر Xcode من جهازك ورفعه لـ TestFlight.
2. الدخول لـ App Store Connect وتغيير قسم "Test Information" وكتابة الحساب (demo / demo1234).
3. الضغط على Submit for Review لإعادة الإرسال.

بالمرفقات التعديلات البرمجية (ملف auth_service.dart).

مع أطيب التحيات،
كبير مهندسي أبل - خبير الذكاء الاصطناعي
"""

    mailto_url = f"mailto:Elhamshariahmed@gmail.com?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
    webbrowser.open(mailto_url)
    print("✅ تم تجهيز الرسالة، يرجى إرفاق الملف يدوياً وإرسالها.")

if __name__ == "__main__":
    zip_location = create_zip_package()
    draft_email(zip_location)

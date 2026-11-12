# منصة حَلَقَات (Halaqat) &mdash; MVP Web Application

منصة ويب متكاملة، متجاوبة، وسريعة لإدارة وتحفيظ القرآن الكريم وتنظيم الحلقات التعليمية والمجتمعات القرآنية. مبنية بأحدث معايير **Django** مع واجهة مستخدم عربية كاملة (RTL) بتصميم عصري وألوان إسلامية مميزة.

---

## 🌟 مميزات المنصة (Core Features)

### 1. إدارة الحسابات والهوية (Accounts & Profiles)
- **نموذج مستخدم مخصص (`Custom User Model`)**: مسجل برقم الهاتف، البريد الإلكتروني، الاسم، الجنس (ذكر / أنثى)، والدور الأساسي (طالب / معلم / مسؤول).
- **تسجيل دخول مرن**: إمكانية تسجيل الدخول عبر **اسم المستخدم، أو البريد الإلكتروني، أو رقم الهاتف**.
- **الأمان والخصوصية**: حظر استخدام رقم الهاتف ككلمة مرور، وحظر كلمات المرور التافهة، وحظر الحسابات المعلقة من الدخول فورياً.
- **ملف شخصي وسجل قرآني**: متابعة إحصائيات الحضور والغياب، ومستويات الأداء في التسميع، والواجبات القادمة.

### 2. إدارة الحلقات القرآنية (Halaqat Management)
- **إنشاء وتعديل الحلقات**: تحديد اسم الحلقة، وصفها، فئتها (رجال / نساء)، ومستوى الخصوصية (عامة / خاصة).
- **الفصل بين الفئات على مستوى السيرفر**: تطبيق القيد الشرعي بأن الطلاب ينضمون فقط للحلقات المطابقة لجنسهم، مع مرونة إدارة المعلمين والمساعدين للحلقات المختلفة.
- **الحلقات العامة والخاصة**: الحلقات العامة تظهر في الاستكشاف وتدعم طلبات الانضمام مع موافقة/رفض الإدارة. الحلقات الخاصة تكون بالدعوة الهاتفية المباشرة فقط.
- **إضافة الأعضاء بالبحث بالهاتف**: دعوة أي طالب أو معلم أو مساعد مسجل في المنصة عبر رقم هاتفه فوراً.
- **صلاحيات تفصيلية للمساعدين**: تخصيص صلاحيات إدارة الجلسات، رصد الحضور، تسجيل التسميع، وإدارة الأعضاء لكل مساعد داخل الحلقة.
- **الجداول الأسبوعية**: تسجيل مواعيد أسبوعية متعددة لكل حلقة بأوقات البدء والانتهاء والملاحظات.

### 3. إدارة الجلسات والاجتماعات (Sessions Management)
- **دورة حياة الجلسة**: حالات الجلسة (`مجدولة SCHEDULED` &rarr; `جارية الآن IN_PROGRESS` &rarr; `مكتملة COMPLETED` &rarr; `ملغاة CANCELLED`).
- **Google Meet**: دعم إرفاق روابط اجتماعات Google Meet للدخول المباشر بنقرة زر.
- **إعادة فتح الجلسات**: إمكانية إعادة فتح الجلسات المكتملة لتتحول تلقائياً إلى جارية مع تسجيل التدقيق (ReopenedBy / ReopenedAt).
- **منع إكمال الملغاة**: حظر إكمال أي جلسة تم إلغاؤها برمجياً.
- **الحذف المؤقت (Soft Delete)**: الاحتفاظ بالجلسات المحذوفة وسجلاتها لأغراض التدقيق مع إخفائها من العرض المعتاد.

### 4. رصد الحضور والغياب (Attendance Tracking)
- حالات حضور دقيقة: `حاضر PRESENT`، `غائب ABSENT`، `متأخر LATE`، `معذور EXCUSED`.
- إضافة ملاحظات مخصصة لكل طالب وتتبع تاريخ وسجل التعديلات (Audit trail).
- صفحة خاصة لكل طالب تعرض سجله الكامل ومعدلات حضوره.

### 5. متابعة التسميع ومستويات الإنجاز (Recitation & Progress)
- تدوين تفصيلي يشمل: **الحفظ الجديد**، **المراجعة القريبة**، **المراجعة البعيدة**، **الواجب القادم**.
- **مستويات تقييم لفظية فقط** (بدون تقييم النجوم): ممتاز، جيد جدًا، جيد، مقبول، ضعيف.
- إتاحة تعديل السجلات وحذفها مؤقتاً لأصحاب الصلاحية.

### 6. نظام المحادثات الفورية (HTTP Polling Chat)
- **نوعان من المحادثات**:
  1. محادثة جماعية لكل حلقة قرآنية تضم جميع أعضائها.
  2. محادثة مباشرة خاصة (1-to-1) بين أي طالب ومعلم أو عضوين.
- **تحديث خفيف بدون WebSockets/Redis**: يعتمد على `Fetch API Polling` كل 3 ثوانٍ لجلب الرسائل الأحدث فقط (`id > last_id`).
- **إيقاف الاستعلام الذكي**: إيقاف Polling تلقائياً عند مغادرة الصفحة أو تصغير التبويب (`document.hidden`).
- **تحميل الرسائل السابقة**: زر "تحميل رسائل أقدم" مع ترقيم وتصفح سلس.

### 7. التنبيهات والإشعارات (In-App Notifications)
- إشعارات فورية عند: إنشاء جلسة جديدة، تعديل موعد، إلغاء جلسة، استلام رسالة شات، إرسال طلب انضمام، أو قبول/رفض طلب.
- عداد الإشعارات غير المقروءة في شريط التنقل مع إمكانية تعليم الكل كمقروء.

### 8. لوحة الإدارة والرقابة (Admin Dashboard)
- إحصائيات عامة للمنصة (إجمالي المستخدمين، الحلقات، الجلسات، التسميع).
- بحث وتصفية متقدمة للمستخدمين حسب الدور، الجنس، وحالة الحساب.
- ميزة **تعليق الحساب (Suspend)** وإعادة التنشيط لمنع أي مستخدم مخالف من الدخول.

---

## 🛠️ البنية التقنية (Technology Stack)

- **Backend**: Python 3.10+ / 3.12+ / 3.15, Django 5/6 (Django ORM, Authentication, CSRF, Forms).
- **Frontend**: Django Templates, HTML5, CSS3 Variables, Vanilla JavaScript, Bootstrap 5.3 RTL, Bootstrap Icons.
- **Database**: SQLite (`db.sqlite3`) للنسخة الحالية، مع توافق كامل للانتقال إلى PostgreSQL مستقبلاً دون تعديل منطق الأعمال.
- **Static & Media**: WhiteNoise (`CompressedManifestStaticFilesStorage` / `StaticFilesStorage`) و Django FileSystemStorage للملفات المرفوعة.

---

## 📂 هيكل المشروع (Project Directory Layout)

```text
Quran web/
├── accounts/               # إدارة المستخدمين، التسجيل، الدخول، السجل القرآني
│   └── management/commands/seed_data.py # أمر توليد البيانات التجريبية
├── halaqat/                # الحلقات، العضويات، المواعيد الأسبوعية، طلبات الانضمام
├── halaqa_sessions/        # الجلسات القرآنية، رابط Meet، دورة حياة الجلسة
├── attendance/             # رصد الحضور والغياب والتدقيق
├── recitations/            # سجلات التسميع ومستويات الإداء والواجبات
├── chat/                   # غرف المحادثة الجماعية والخاصة و APIs الخاصة بالـ Polling
├── notifications/          # مركز الإشعارات والتنبيهات
├── dashboard/              # لوحة إدارة ورقابة المنصة
├── config/                 # إعدادات Django، التوجيهات URLs، WSGI
├── templates/              # قوالب HTML متجاوبة تدعم RTL ومبوبة حسب التطبيقات
├── static/                 # ملفات CSS, JS, الأيقونات
├── media/                  # الصور والملفات المرفوعة
├── pythonanywhere_wsgi.py  # ملف تكوين WSGI الجاهز لـ PythonAnywhere
├── requirements.txt        # مكتبات بايثون المطلوبة
├── .env.example            # مثال لمتغيرات البيئة
├── manage.py
└── README.md
```

---

## 🚀 التشغيل المحلي السريع (Local Development Setup)

### 1. استنساخ المستودع وإنشاء البيئة الافتراضية
```bash
# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة الافتراضية
# على Windows PowerShell:
.\venv\Scripts\Activate.ps1
# على Linux/macOS:
source venv/bin/activate
```

### 2. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 3. إعداد متغيرات البيئة
قم بإنشاء ملف `.env` (أو انسخ `.env.example`):
```ini
SECRET_KEY=local-dev-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.pythonanywhere.com
```

### 4. تطبيق الهجرات وتجميع الملفات
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. تعبئة البيانات التجريبية الجاهزة (Seed Data)
يقوم هذا الأمر بإنشاء حسابات جاهزة لجميع الأدوار (مسؤول، معلمين، طلاب) وحلقات وجلسات ورسائل شات:
```bash
python manage.py seed_data
```

### 6. تشغيل السيرفر المحلي
```bash
python manage.py runserver
```
ثم افتح المتصفح على: `http://127.0.0.1:8000/`

---

## 🔑 الحسابات التجريبية الجاهزة (Demo Accounts)

جميع الحسابات تعمل بكلمات المرور الموضحة أدناه، ويمكن تسجيل الدخول برقم الهاتف أو اسم المستخدم أو البريد:

| الدور | الاسم | اسم المستخدم | الهاتف | البريد | كلمة المرور |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **مسؤول المنصة** | مدير المنصة | `admin` | `0500000000` | `admin@quran.com` | `Admin@123456` |
| **معلم (رجال)** | الشيخ أحمد الغامدي | `teacher_ahmed` | `0511111111` | `ahmed@quran.com` | `Teacher@123456` |
| **معلمة (نساء)** | خديجة الأنصاري | `teacher_khadija` | `0522222222` | `khadija@quran.com` | `Teacher@123456` |
| **طالب (ذكر)** | عمر سالم | `student_omar` | `0533333333` | `omar@quran.com` | `Student@123456` |
| **طالبة (أنثى)** | مريم حسن | `student_maryam` | `0544444444` | `maryam@quran.com` | `Student@123456` |

---

## 🧪 تشغيل الاختبارات المؤتمتة (Automated Tests)

المشروع مزود بحزمة اختبارات شاملة تغطي الصلاحيات، القيود الشرعية للفئات، أمان تسجيل الدخول، دورة حياة الجلسات، رصد الحضور والتسميع، وصلاحيات الشات:

```bash
python manage.py test
```

---

## 🌐 دليل النشر على بايثون إني وير (PythonAnywhere Deployment Guide)

تم تجهيز هذا المشروع ليتوافق 100% مع بيئة **PythonAnywhere** المجانية والمدفوعة:

### 1. رفع الكود عبر Git على PythonAnywhere
افتح Bash Console على PythonAnywhere:
```bash
cd ~
git clone <your-github-repo-url> quran-app
cd ~/quran-app
```

### 2. إنشاء البيئة الافتراضية وتثبيت المتطلبات
```bash
mkvirtualenv --python=python3.10 quran-venv
# أو
python3.10 -m venv ~/quran-venv
source ~/quran-venv/bin/activate
cd ~/quran-app
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. إعداد ملف البيئة `.env` في السيرفر
```bash
cat << 'EOF' > ~/quran-app/.env
SECRET_KEY=production-strong-random-key-replace-this-now!
DEBUG=False
ALLOWED_HOSTS=<your-username>.pythonanywhere.com
EOF
```

### 4. تطبيق الهجرات وتجميع الملفات الساكنة
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data   # اختياري لتوليد حسابات أولية
```

### 5. ضبط إعدادات Web Tab في PythonAnywhere
في لوحة تحكم **Web Tab**:
- **Source code**: `/home/<your-username>/quran-app`
- **Working directory**: `/home/<your-username>/quran-app`
- **Virtualenv**: `/home/<your-username>/quran-venv`

#### ضبط Static files في Web Tab:
| URL | Directory |
| :--- | :--- |
| `/static/` | `/home/<your-username>/quran-app/staticfiles` |
| `/media/` | `/home/<your-username>/quran-app/media` |

#### ضبط ملف WSGI Configuration:
اضغط على رابط ملف الـ WSGI (مثلاً `/var/www/<your-username>_pythonanywhere_com_wsgi.py`)، واستبدل محتواه بالمحتوى التالي الموجود في ملف `pythonanywhere_wsgi.py`:
```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = '/home/<your-username>/quran-app'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

env_path = Path(PROJECT_DIR) / '.env'
if env_path.exists():
    load_dotenv(env_path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
اضغط على زر **Save** ثم اضغط زر **Reload <your-username>.pythonanywhere.com**.

---

## 💾 سياسة النسخ الاحتياطي لقاعدة البيانات والملفات (Backups)

1. **قاعدة البيانات (`db.sqlite3`)**:
   - تقع قاعدة البيانات في مجلد المشروع الدائم.
   - يُوصى بجدولة مهمة يومية عبر تبويب **Tasks** في PythonAnywhere لأخذ نسخة احتياطية:
     ```bash
     mkdir -p ~/backups && cp ~/quran-app/db.sqlite3 ~/backups/db_$(date +\%Y\%m\%d).sqlite3
     ```
2. **الملفات المرفوعة (`media/`)**:
   - يتم تخزين الصور الشخصية في `~/quran-app/media/`.
   - يمكن أخذ نسخة مضغوطة أسبوعياً:
     ```bash
     tar -czf ~/backups/media_$(date +\%Y\%m\%d).tar.gz -C ~/quran-app media
     ```
3. **الأمان**: لا تقم مطلقاً بنشر ملف `.env` أو قاعدة البيانات الحية `db.sqlite3` على المستودع العام في GitHub (تم إدراجها بالفعل في ملف `.gitignore`).

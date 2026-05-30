# רשימת תיוג ציות ופרטיות — סוכן הרכש PTG

**גרסה:** 1.0  
**תאריך עדכון אחרון:** 2026-05-30  
**אחראי:** מנהל אבטחת מידע (CISO) / DPO  

---

## א. נתוני ספקים — הסכם עיבוד נתונים (DPA)

- [ ] **האם נדרש Data Processing Agreement (DPA) עם כל ספק?**  
  כן, אם הסוכן שומר נתונים אישיים של אנשי קשר בחברות הספקים (שם, כתובת מייל, מספר טלפון) — חל GDPR/תקנות הגנת הפרטיות הישראליות.

- [ ] נחתם DPA עם כל ספק שנתוניו נשמרים ב-Azure Table Storage.
- [ ] רשימת הספקים ומעמד ה-DPA שלהם מתועדת ומעודכנת.
- [ ] ספקים שלא חתמו DPA — נתוניהם מינימליים (אנונימיזציה של שם האיש קשר במידת האפשר).
- [ ] בחינת מעמד הסוכן: האם הוא **Data Processor** (מעבד נתונים) או **Data Controller** (בעל נתונים)?  
  ✅ הסוכן פועל בשם הארגון → הארגון הוא ה-Controller, הסוכן הוא ה-Processor.

---

## ב. שמירת מיילים — כמה זמן מותר לשמור?

- [ ] **מיילים ב-Azure Table Storage (RFQ records):**  
  יש להגדיר מדיניות retention — המלצה: **24 חודשים** לצרכי ביקורת עסקית, ואחר כך מחיקה אוטומטית.

- [ ] **מיילים ב-Outlook / Exchange Online:**  
  לפי מדיניות הארגון — בדרך כלל 7 שנים לצורכי ביקורת פנימית.

- [ ] גוף המייל (body) של ספקים **לא** נשמר ב-Azure Table Storage (רק סיכום ומטא-דאטה).  
  ✅ בדוק: `RFQRecord` ב-`agent/models.py` — לא כולל שדה `body`. אם נוסף בעתיד — נדרש DPA.

- [ ] נוהל מחיקה פורמלי (Right to Erasure / GDPR Article 17) מתועד ובוצע בדיקה.
- [ ] כל שינוי במדיניות retention מתועד ב-changelog.

---

## ג. GDPR ופרטיות — מה נשמר ואיפה?

### מיפוי נתונים אישיים

| נתון | מיקום אחסון | בסיס עיבוד (Lawful Basis) | תקופת שמירה |
|------|------------|--------------------------|-------------|
| כתובת מייל ספק | Azure Table Storage (`supplier_email`) | Legitimate Interest | 24 חודשים |
| שם ספק | Azure Table Storage (`supplier_name`) | Contract | 24 חודשים |
| מייל מהנדס פנימי | Azure Table Storage (`engineer_assigned`) | Contract | 24 חודשים |
| הודעות Slack (לוגים) | Slack infrastructure | Legitimate Interest | 90 ימים |
| Application Insights logs | Azure Monitor | Legitimate Interest | 90 ימים |

- [ ] **Privacy Impact Assessment (PIA)** בוצע לפני העלאה לייצור.
- [ ] נתונים אישיים **לא** נשלחים ל-Anthropic API מעבר למה שנדרש לסיווג — אין שליחת שמות מלאים, מספרי טלפון, או מידע רגיש נוסף.
- [ ] ה-prompt ל-Claude כולל רק Subject, Sender domain, ו-Body (מסונן) — לא full contact details.
- [ ] נוהל תגובה לבקשת Subject Access Request (SAR) מוגדר ותועד.
- [ ] העברות נתונים אל מחוץ ל-EEA: בדוק מיקום Azure region (West Europe / North Europe מומלצים).

---

## ד. גיבויים של Azure Table Storage

- [ ] **Geo-redundant storage (GRS)** מופעל על ה-Storage Account.
- [ ] גיבוי יומי אוטומטי מוגדר דרך Azure Backup או Export לבלוב.
- [ ] נבדקה יכולת שחזור (Restore) לפחות אחת לרבעון.
- [ ] גיבויים מוגנים ב-immutable storage (WORM) למניעת מחיקה זדונית.
- [ ] גיבויים מאוחסנים ב-region שונה מה-primary (Disaster Recovery).
- [ ] נוהל RPO (Recovery Point Objective) מוגדר: **מקסימום 24 שעות של אובדן נתונים**.
- [ ] נוהל RTO (Recovery Time Objective) מוגדר: **מקסימום 4 שעות להחזרת שירות**.

---

## ה. מדיניות Rotation של API Keys

| סוד | תדירות Rotation מומלצת | שיטה |
|-----|------------------------|------|
| `ANTHROPIC_API_KEY` | כל 90 יום | הפקת מפתח חדש ב-Anthropic Console, עדכון ב-Key Vault |
| `AZURE_CLIENT_SECRET` | כל 90 יום | Azure AD App Registration → New Secret |
| `SLACK_BOT_TOKEN` | כל 180 יום | Slack App Management → Regenerate |
| `PRIORITY_PASSWORD` | כל 90 יום | עדכון ב-Priority ERP + Key Vault |
| `SLACK_SIGNING_SECRET` | כל 180 יום | Slack App Management → Regenerate |
| Webhook HMAC Secret | כל 90 יום | עדכון ב-Key Vault + deployment חדש |

- [ ] כל ה-secrets מאוחסנים ב-**Azure Key Vault** ולא כ-environment variables קבועים.
- [ ] תהליך rotation אוטומטי מוגדר ב-Azure Key Vault (Auto-rotation Policy).
- [ ] לאחר rotation — מפתח ישן מושבת (לא רק מבוטל) להמנעות מ-race condition.
- [ ] בדיקת deployment לאחר כל rotation — ודא שהמערכת עובדת עם המפתח החדש.
- [ ] תיעוד כל rotation ב-audit log.

---

## ו. מי רשאי לגשת ל-Key Vault?

- [ ] **עיקרון Least Privilege:** רק ה-Azure Managed Identity של Azure Function מקבלת **Get/List** secrets.
- [ ] **DevOps / Infrastructure team:** גישת **Set** (לכתיבת secrets חדשים) — לא Get לערכים קיימים.
- [ ] **אף מפתח** לא אמור לגשת לערכי secrets בייצור — רק ב-Key Vault Access Policies.
- [ ] **CISO / Security lead:** גישת ניהול (Purge, manage) — לא ל-secret values.
- [ ] Access Policies מבוססות על **Azure RBAC** (לא Legacy Access Policies).
- [ ] הפעלת **Azure Key Vault Soft Delete** + **Purge Protection** (90 ימים).
- [ ] ניטור: Azure Defender for Key Vault + Alerts על גישה חריגה.
- [ ] ביקורת רבעונית של הרשאות — מחיקת גישות שאינן נדרשות.
- [ ] MFA חובה לכל אדם עם גישה ל-Key Vault דרך Azure Portal.

---

## ז. Incident Response — מה עושים אם נגנב מפתח?

### נוהל תגובה לאירוע (Playbook)

**שלב 1 — גילוי וזיהוי (0–15 דקות)**
- [ ] מקבל התראה (Azure Defender / Anthropic anomaly / ידנית) → מאשר שמדובר בגניבת מפתח.
- [ ] מתעד את זמן הגילוי ופרטי האירוע ב-incident log.
- [ ] מודיע ל-CISO ו-IT Manager.

**שלב 2 — בלימה מיידית (15–30 דקות)**
- [ ] **Anthropic API Key:** התחבר ל-https://console.anthropic.com → Revoke key immediately.
- [ ] **Azure Client Secret:** Azure Portal → App Registration → Delete compromised secret.
- [ ] **Slack Token:** api.slack.com → Revoke token.
- [ ] **Priority ERP:** שנה סיסמה ב-Priority + בטל session קיים.
- [ ] Webhook Secret: עדכן ב-Key Vault → redeploy Azure Function.

**שלב 3 — חקירה (30 דקות – 4 שעות)**
- [ ] בדוק Azure Activity Log ו-Application Insights מה נגנב ומתי.
- [ ] חפש שימוש לא מורשה: קריאות API חריגות, מיילים שנשלחו, שינויים ב-ERP.
- [ ] שמור logs לצורכי חקירה (אל תמחק!).
- [ ] קבע scope — האם נחשפו נתוני ספקים? נתוני עובדים?

**שלב 4 — החזרה לפעילות (4–24 שעות)**
- [ ] הפקת secrets חדשים → עדכון ב-Key Vault → deployment חדש.
- [ ] אימות שהמערכת פועלת עם credentials חדשים.
- [ ] סריקת codebase ב-git history לדליפת secrets (כלי: `git-secrets` / `trufflehog`).

**שלב 5 — דיווח (24–72 שעות)**
- [ ] אם נחשפו נתונים אישיים של אנשים באיחוד האירופי: **דיווח ל-DPA תוך 72 שעות** (GDPR Article 33).
- [ ] אם נחשפו נתונים אישיים של ספקים ישראלים: דיווח לרשם מאגרי המידע.
- [ ] תיעוד פורמלי של האירוע + lessons learned.
- [ ] עדכון מודל האיומים ונהלי האבטחה.

---

## ח. בדיקות תקופתיות

- [ ] **Penetration Testing:** לפחות פעם בשנה, כולל בדיקת Prompt Injection ו-API endpoints.
- [ ] **Dependency Scan:** `pip audit` / `safety check` — בכל release.
- [ ] **Static Analysis:** `bandit -r .` — בכל CI/CD pipeline.
- [ ] **Secret Scan:** `trufflehog` על ה-git repository — בכל push.
- [ ] **Access Review:** רבעוני — מי יש לו גישה ל-Key Vault, Azure, Slack, Priority ERP.

---

*מסמך זה יש לסקור ולעדכן לפחות פעם בשנה, או לאחר כל שינוי ארכיטקטורלי משמעותי.*

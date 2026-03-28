# LINE Hotspot Notification Bot 🔥

แจ้งเตือนจุดความร้อน (Hotspot) จากดาวเทียม VIIRS ผ่าน LINE กลุ่ม

## สถาปัตยกรรม

```
GISTDA Directory API ──→ ดึง list ไฟล์ Excel วันนี้ (4 ดาวเทียม)
  (G_Vi1_Tim, N_Vi1_Tim, N_Vi2_Tim, N_Vi3_Tim)
                        │
                        ▼
        Pre-filter ไฟล์ตาม Time Window (filename ±30 นาที)
                        │
                        ▼
        GISTDA Excel Download ──→ อ่านเวลาจริงจาก COL_TIME (Thai TZ)
                        │
                        ▼
        Filter Hotspots ตาม COL_TIME ตรง Time Window
                        │
                        ▼
        บันทึก Latest Hotspot Time → .hotspot_state (GitHub Actions)
                        │
                        ▼
        Message Formatter ──→ จัดรูปแบบข้อความ 2 แบบ
          • แบ่งตามแหล่งข้อมูล (ดาวเทียม)
          • แบ่งตามอำเภอ
                        │
                        ▼
        LINE Push Message API ──→ ส่งแจ้งเตือนเข้ากลุ่ม LINE
```

## คุณสมบัติ

- ดึงรายการ Excel จาก GISTDA directory API โดยตรง — **ไม่ต้องใช้ FIRMS API หรือ API Key ใด ๆ**
- คัดกรอง hotspot จาก **COL_TIME จริงในไฟล์ Excel** (เวลา satellite acquisition, Thai TZ)
- รองรับดาวเทียม 4 ดวง: **Suomi NPP (GISTDA)**, **Suomi NPP (NASA)**, **NOAA-20**, **NOAA-21**
- **Dynamic Time Window** — รอบถัดไปเริ่มต่อจาก hotspot ล่าสุดที่พบ (บันทึกใน `.hotspot_state`)
- แจ้งเตือน **8 รอบ/วัน** ด้วย window ที่ไม่ overlap กัน
- ข้อความ 2 รูปแบบ: แบ่งตามดาวเทียม + แบ่งตามอำเภอ
- แยก bubble อัตโนมัติเมื่อจุดความร้อน ≥ 11 จุด — จำกัดไม่เกิน 40 จุด/bubble
- รายงานเป็นภาษาไทย พร้อมลิงก์ Google Maps

## รอบการแจ้งเตือน (GitHub Actions)

| รอบ | เวลา (ICT) | Time Window | หมายเหตุ |
| --- | ---------- | ----------- | -------- |
| 1 | 05:25 | 00:00 – 05:25 | Reset ทุกวัน — เริ่มจาก 00:00 เสมอ |
| 2 | 11:00 | `LAST` – 11:00 | `LAST` = latest hotspot time จากรอบก่อน |
| 3 | 12:00 | `LAST` – 12:00 | |
| 4 | 13:00 | `LAST` – 13:00 | |
| 5 | 14:00 | `LAST` – 14:00 | |
| 6 | 15:00 | `LAST` – 15:00 | |
| 7 | 16:00 | `LAST` – 16:00 | |
| 8 | 17:00 | `LAST` – 17:00 | |

> ถ้าไม่พบ hotspot ในรอบใด → `LAST` ไม่เปลี่ยน → รอบถัดไปครอบคลุมช่วงเวลาที่กว้างขึ้น

## โครงสร้างไฟล์

| ไฟล์                    | คำอธิบาย                                             |
| ----------------------- | ---------------------------------------------------- |
| `main.py`               | จุดเริ่มต้น — scheduler หรือ `--now` สำหรับรันทันที  |
| `config.py`             | ตั้งค่าต่าง ๆ จาก environment variables              |
| `gistda_excel.py`       | List / download / parse Excel + คืน latest hotspot time |
| `message_formatter.py`  | จัดรูปแบบข้อความแจ้งเตือน                            |
| `line_bot.py`           | ส่งข้อความไปยังกลุ่ม LINE (Push Message API)         |
| `webhook_server.py`     | ใช้ครั้งเดียวเพื่อหา Group ID                        |
| `test_bot.py`           | ทดสอบ pipeline ทั้งหมด + edge cases                  |
| `test_fetch.py`         | ดูตัวอย่างข้อความจริงโดยไม่ส่ง LINE                  |
| `.hotspot_state`        | บันทึก latest hotspot time (auto-managed โดย CI)     |

## ขั้นตอนการติดตั้ง

### 1. สร้าง LINE Official Account & Messaging API

1. ไปที่ [LINE Developers Console](https://developers.line.biz/)
2. สร้าง Provider → สร้าง Messaging API Channel
3. ในแท็บ **Messaging API** → ออก **Channel Access Token** (long-lived)
4. ปิด **Auto-reply messages** (ตั้งเป็น Disabled)

### 2. หา Group ID ด้วย ngrok + Webhook Server

> **หมายเหตุ:** ขั้นตอนนี้ทำครั้งเดียวเพื่อหา Group ID เท่านั้น
> หลังจากได้ Group ID แล้ว ไม่จำเป็นต้องใช้ ngrok หรือ webhook อีก

**Terminal 1** — รัน webhook server:

```bash
python webhook_server.py
```

**Terminal 2** — รัน ngrok:

```bash
ngrok http 8000
```

**ตั้งค่า Webhook ใน LINE Developers Console:**

1. ไปที่แท็บ **Messaging API** → **Webhook URL**
2. ใส่ URL จาก ngrok เช่น `https://abcd-1234.ngrok-free.app`
3. กด **Update** → กด **Verify** (ควรขึ้น Success)
4. เปิด **Use webhook** → **ON**

**เพิ่มบอทเข้ากลุ่ม LINE:**

1. สแกน QR Code จากแท็บ Messaging API เพื่อเพิ่มบอทเป็นเพื่อน
2. เชิญบอทเข้ากลุ่ม LINE ที่ต้องการ
3. ส่งข้อความในกลุ่ม → ดูที่ Terminal 1 จะเห็น Group ID:
   ```
   🎉 GROUP ID FOUND!
   GROUP ID: C1234567890abcdef...
   👉 นำค่านี้ไปใส่ใน .env → LINE_GROUP_ID=C1234567890abcdef...
   ```
4. คัดลอก Group ID ไปใส่ใน `.env`
5. หยุด webhook server (Ctrl+C) และ ngrok

### 3. ติดตั้ง Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. ตั้งค่า Environment Variables

```bash
cp .env.example .env
# แก้ไขไฟล์ .env ใส่ค่าจริง
```

| ตัวแปร                      | คำอธิบาย                                        | ค่าเริ่มต้น                                  |
| --------------------------- | ----------------------------------------------- | -------------------------------------------- |
| `LINE_CHANNEL_ACCESS_TOKEN` | Token จาก LINE Developers Console               | (ต้องระบุ)                                   |
| `LINE_GROUP_ID`             | Group ID ของกลุ่ม LINE                          | (ต้องระบุ)                                   |
| `PROVINCE_FILTER`           | ชื่อจังหวัดที่กรอง                              | `ลำพูน`                                      |
| `SCHEDULE_TIMES`            | เวลาแจ้งเตือน (คั่นด้วย `,`) สำหรับ local run  | `05:25,11:00,12:00,13:00,14:00,15:00,16:00,17:00` |
| `MESSAGE_MODE`              | รูปแบบข้อความ: `satellite`, `district`, `both`  | `satellite`                                  |
| `WINDOW_START`              | เวลาเริ่มต้น window (HHMM) — set โดย CI อัตโนมัติ | (ว่าง = 00:00)                              |
| `WINDOW_END`                | เวลาสิ้นสุด window (HHMM) — set โดย CI อัตโนมัติ | (ว่าง = เวลาปัจจุบัน)                       |

## การใช้งาน

```bash
# รันแบบ Scheduler (แจ้งเตือนตามเวลาที่กำหนด)
python main.py

# รันทดสอบทันที 1 ครั้ง (ส่ง LINE จริง)
python main.py --now

# ดูตัวอย่างข้อความโดยไม่ส่ง LINE
python test_fetch.py
python test_fetch.py --window-start 0000 --window-end 0525
python test_fetch.py --date 2026-03-28 --time 11:00 --window-start 0300 --window-end 1100

# ทดสอบ pipeline ทั้งหมด
python test_bot.py
python test_bot.py --date 2026-03-28 --window-start 0000 --window-end 0525
```

## การ Deploy

### ตัวเลือกที่ 1: GitHub Actions (แนะนำ — ฟรี)

วิธีนี้ไม่ต้องมี server ใด ๆ GitHub จะรันบอทตามเวลาที่กำหนดให้อัตโนมัติ

**ขั้นตอน:**

1. Push โปรเจ็กต์ขึ้น GitHub (private repo)

2. ตั้งค่า secrets ใน **Settings → Secrets and variables → Actions → New repository secret**:
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_GROUP_ID`

3. ไฟล์ `.github/workflows/notify.yml` (มีอยู่ใน repo แล้ว) จะรันอัตโนมัติ 8 รอบ/วัน
   และจัดการ `.hotspot_state` ให้อัตโนมัติผ่าน `contents: write` permission

> **หมายเหตุ:** GitHub Actions free tier ให้ 2,000 นาที/เดือน
> บอทนี้ใช้ประมาณ 360 นาที/เดือน (18% ของ free tier)
>
> เมื่อรันมือจากหน้า Actions จะมี dropdown ให้เลือก `MESSAGE_MODE` (satellite / district / both)
> และสามารถระบุ `WINDOW_START` / `WINDOW_END` เองได้

### ตัวเลือกที่ 2: crontab (Linux)

```bash
crontab -e

# เพิ่มบรรทัด (เวลาเป็น UTC)
25 22 * * * cd /path/to/line-hotspot-noti && WINDOW_START=0000 WINDOW_END=0525 /path/to/venv/bin/python main.py --now
00  4 * * * cd /path/to/line-hotspot-noti && WINDOW_END=1100 /path/to/venv/bin/python main.py --now
```

## รูปแบบข้อความ (`MESSAGE_MODE`)

| โหมด        | คำอธิบาย                                              | ค่าเริ่มต้น |
| ----------- | ----------------------------------------------------- | ----------- |
| `satellite` | แบ่งตามแหล่งข้อมูล (ดาวเทียม → เวลา → ตำบล/อำเภอ)    | ✅          |
| `district`  | แบ่งตามอำเภอ (อำเภอ → ตำบล พร้อมระบุดาวเทียมและเวลา) |             |
| `both`      | ส่งทั้ง 2 รูปแบบ คั่นด้วย separator                  |             |

### การแยก Bubble (โหมด satellite)

เมื่อจุดความร้อน **≥ 11 จุด** ระบบจะแยก bubble อัตโนมัติ:

1. แต่ละดาวเทียม+เวลา เริ่ม bubble ใหม่
2. แต่ละ bubble มีได้ไม่เกิน 40 จุด
3. อำเภอที่เกิน 40 จุด → มี bubble เฉพาะ ไม่ผสมกับอำเภออื่น
4. เรียง bubble ตามอำเภอจากจำนวนจุดมากไปน้อย

## หมายเหตุทางเทคนิค

- ไฟล์ Excel จาก GISTDA เก็บเวลาจริงของ satellite pass ใน column "เวลา" (Thai TZ, HHMM)
- ไฟล์ Excel ที่ดาวน์โหลดจะถูกเก็บเป็น temp file และลบทิ้งทันทีหลัง parse
- LINE Push Message API รองรับสูงสุด 5 bubbles ต่อ request — บอทจะแบ่ง batch อัตโนมัติ
- `.hotspot_state` ถูก commit อัตโนมัติโดย GitHub Actions พร้อม `[skip ci]` เพื่อไม่ trigger workflow ซ้ำ

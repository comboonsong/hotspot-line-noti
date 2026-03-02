# LINE Hotspot Notification Bot 🔥

แจ้งเตือนจุดความร้อน (Hotspot) จากดาวเทียม VIIRS ผ่าน LINE กลุ่ม

## สถาปัตยกรรม

```
NASA FIRMS API ──→ ค้นหาเวลาผ่านดาวเทียม (pass times)
                        │
                        ▼
        GISTDA Excel Download ──→ ดึงรายละเอียดจุดความร้อน
          (NASA folder: N_Vi1, N_Vi2, N_Vi3)
          (GISTDA folder: G_Vi1)
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

- ดึงข้อมูล pass times จาก [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/)
- ดาวน์โหลดรายงาน Excel จาก GISTDA ทั้งโฟลเดอร์ NASA (N\_) และ GISTDA (G\_)
- รองรับดาวเทียม 3 ดวง: **Suomi NPP**, **NOAA-20**, **NOAA-21**
- แจ้งเตือน Suomi NPP จาก 2 แหล่ง: NASA และ GISTDA แยกกัน
- แบ่งรอบการแจ้งเตือน: **00:00–11:59** (รอบเช้า) และ **12:00–23:59** (รอบบ่าย)
- ข้อความ 2 รูปแบบ: แบ่งตามดาวเทียม + แบ่งตามอำเภอ
- แยก bubble อัตโนมัติเมื่อจุดความร้อน ≥ 11 จุด (ป้องกันข้อความยาวเกินลิมิต LINE 5,000 ตัวอักษร)
- รายงานเป็นภาษาไทย พร้อมลิงก์ Google Maps

## โครงสร้างไฟล์

| ไฟล์                   | คำอธิบาย                                            |
| ---------------------- | --------------------------------------------------- |
| `main.py`              | จุดเริ่มต้น — scheduler หรือ `--now` สำหรับรันทันที |
| `config.py`            | ตั้งค่าต่าง ๆ จาก environment variables             |
| `firms_api.py`         | ดึง pass times จาก NASA FIRMS API                   |
| `gistda_excel.py`      | ดาวน์โหลดและ parse Excel จาก GISTDA                 |
| `message_formatter.py` | จัดรูปแบบข้อความแจ้งเตือน                           |
| `line_bot.py`          | ส่งข้อความไปยังกลุ่ม LINE (Push Message API)        |
| `webhook_server.py`    | ใช้ครั้งเดียวเพื่อหา Group ID                       |
| `test_bot.py`          | ทดสอบ pipeline ทั้งหมด + edge cases                 |
| `test_fetch.py`        | ดูตัวอย่างข้อความจริงโดยไม่ส่ง LINE                 |

## ขั้นตอนการติดตั้ง

### 1. สร้าง LINE Official Account & Messaging API

1. ไปที่ [LINE Developers Console](https://developers.line.biz/)
2. สร้าง Provider → สร้าง Messaging API Channel
3. ในแท็บ **Messaging API** → ออก **Channel Access Token** (long-lived)
4. ปิด **Auto-reply messages** (ตั้งเป็น Disabled)

### 2. หา Group ID ด้วย ngrok + Webhook Server

> **หมายเหตุ:** ขั้นตอนนี้ทำครั้งเดียวเพื่อหา Group ID เท่านั้น
> หลังจากได้ Group ID แล้ว ไม่จำเป็นต้องใช้ ngrok หรือ webhook อีก
> เพราะบอทใช้ Push Message API (ส่งข้อความออกอย่างเดียว)

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
6. ปิด webhook ใน LINE Developers Console ได้ (ไม่จำเป็นต้องเปิดอีก)

### 3. ติดตั้ง Dependencies

```bash
# สร้าง virtual environment (แนะนำ)
python3 -m venv venv
source venv/bin/activate

# ติดตั้ง packages
pip install -r requirements.txt
```

### 4. ตั้งค่า Environment Variables

```bash
cp .env.example .env
# แก้ไขไฟล์ .env ใส่ค่าจริง
```

| ตัวแปร                      | คำอธิบาย                                       | ค่าเริ่มต้น               |
| --------------------------- | ---------------------------------------------- | ------------------------- |
| `LINE_CHANNEL_ACCESS_TOKEN` | Token จาก LINE Developers Console              | (ต้องระบุ)                |
| `LINE_GROUP_ID`             | Group ID ของกลุ่ม LINE                         | (ต้องระบุ)                |
| `FIRMS_MAP_KEY`             | API Key จาก NASA FIRMS                         | (ต้องระบุ)                |
| `PROVINCE_FILTER`           | ชื่อจังหวัดที่กรอง                             | `ลำพูน`                   |
| `SCHEDULE_TIMES`            | เวลาแจ้งเตือน (คั่นด้วย `,`)                   | `01:00,03:00,06:00,14:00` |
| `TIME_SPREAD`               | Tolerance เวลาสำหรับ NASA folder (นาที)        | `5`                       |
| `GISTDA_TIME_SPREAD`        | Tolerance เวลาสำหรับ GISTDA folder (นาที)      | `10`                      |
| `MESSAGE_MODE`              | รูปแบบข้อความ: `satellite`, `district`, `both` | `satellite`               |

## การใช้งาน

```bash
# รันแบบ Scheduler (แจ้งเตือนตามเวลาที่กำหนด)
python main.py

# รันทดสอบทันที 1 ครั้ง (ส่ง LINE จริง)
python main.py --now

# ดูตัวอย่างข้อความโดยไม่ส่ง LINE
python test_fetch.py
python test_fetch.py --mode district
python test_fetch.py --mode both

# ทดสอบ pipeline ทั้งหมด
python test_bot.py
python test_bot.py --date 2026-03-01 --time 11:00
```

## การ Deploy

### ตัวเลือกที่ 1: GitHub Actions (แนะนำ — ฟรี)

วิธีนี้ไม่ต้องมี server ใด ๆ GitHub จะรันบอทตามเวลาที่กำหนดให้อัตโนมัติ

**ขั้นตอน:**

1. Push โปรเจ็กต์ขึ้น GitHub (private repo ได้)

2. ตั้งค่า secrets ใน **Settings → Secrets and variables → Actions → New repository secret**:
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_GROUP_ID`
   - `FIRMS_MAP_KEY`

3. ไฟล์ `.github/workflows/notify.yml` (มีอยู่ใน repo แล้ว):

```yaml
name: Hotspot Notification

on:
  schedule:
    # เวลา cron เป็น UTC (ไทย UTC+7)
    # Shifting 25 mins past the hour to avoid GitHub congestion
    # 05:25 ICT = 22:25 UTC (วันก่อนหน้า)
    - cron: "25 22 * * *"
    # 14:25 ICT = 07:25 UTC
    - cron: "25 7 * * *"
    # 18:25 ICT = 11:25 UTC
    - cron: "25 11 * * *"
  workflow_dispatch:
    inputs:
      message_mode:
        description: "Message format"
        required: false
        default: "satellite"
        type: choice
        options:
          - satellite
          - district
          - both

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Set timezone
        run: echo "TZ=Asia/Bangkok" >> $GITHUB_ENV

      - name: Run notification
        run: python main.py --now
        env:
          LINE_CHANNEL_ACCESS_TOKEN: ${{ secrets.LINE_CHANNEL_ACCESS_TOKEN }}
          LINE_GROUP_ID: ${{ secrets.LINE_GROUP_ID }}
          FIRMS_MAP_KEY: ${{ secrets.FIRMS_MAP_KEY }}
          MESSAGE_MODE: ${{ github.event.inputs.message_mode || 'satellite' }}
```

> **หมายเหตุ:** GitHub Actions free tier ให้ 2,000 นาที/เดือน
> บอทนี้ใช้ประมาณ 30 นาที/เดือน (1.5% ของ free tier)
>
> เมื่อรันมือจากหน้า Actions จะมี dropdown ให้เลือก `MESSAGE_MODE` (satellite / district / both)
> เมื่อรันแบบ schedule จะใช้ค่าเริ่มต้น `satellite`

### ตัวเลือกที่ 2: crontab (Linux)

```bash
# แก้ไข crontab
crontab -e

# เพิ่มบรรทัด (ปรับเวลาตามต้องการ)
25 5 * * * cd /path/to/line-hotspot-noti && /path/to/venv/bin/python main.py --now
25 14 * * * cd /path/to/line-hotspot-noti && /path/to/venv/bin/python main.py --now
25 18 * * * cd /path/to/line-hotspot-noti && /path/to/venv/bin/python main.py --now
```

### ตัวเลือกที่ 3: systemd (Linux)

```bash
sudo nano /etc/systemd/system/line-hotspot.service
```

```ini
[Unit]
Description=LINE Hotspot Notification Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/line-hotspot-noti
ExecStart=/path/to/line-hotspot-noti/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable line-hotspot
sudo systemctl start line-hotspot
```

## รูปแบบข้อความ (`MESSAGE_MODE`)

เลือกได้ 3 โหมดผ่าน environment variable `MESSAGE_MODE`:

| โหมด        | คำอธิบาย                                             | ค่าเริ่มต้น |
| ----------- | ---------------------------------------------------- | ----------- |
| `satellite` | แบ่งตามแหล่งข้อมูล (ดาวเทียม → เวลา → ตำบล/อำเภอ)    | ✅          |
| `district`  | แบ่งตามอำเภอ (อำเภอ → ตำบล พร้อมระบุดาวเทียมและเวลา) |             |
| `both`      | ส่งทั้ง 2 รูปแบบ คั่นด้วย separator                  |             |

### การเรียงลำดับ

- **satellite**: เรียงตามดาวเทียม Suomi NPP → Suomi NPP - GISTDA → NOAA-20 → NOAA-21
- **district**: เรียงตามจำนวนจุดความร้อนจากมากไปน้อย

### การแยก Bubble

- ถ้าจุดความร้อน **< 11 จุด** → รวมเป็น 1 bubble ต่อรูปแบบ
- ถ้าจุดความร้อน **≥ 11 จุด** → แยก bubble ตามดาวเทียม (แบบ satellite) หรือตามอำเภอ (แบบ district)

## หมายเหตุทางเทคนิค

- ไฟล์ Excel ที่ดาวน์โหลดจะถูกเก็บเป็น temp file และลบทิ้งทันทีหลัง parse
- LINE Push Message API รองรับสูงสุด 5 bubbles ต่อ request — บอทจะแบ่ง batch อัตโนมัติ
- GISTDA folder (G_Vi1) อาจมีข้อมูลเร็วกว่า FIRMS API ในบางกรณี
- เวลา tolerance สำหรับ GISTDA folder กว้างกว่า NASA folder (10 vs 5 นาที) เพื่อรองรับความต่างของ timestamp

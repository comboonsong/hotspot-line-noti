# LINE Hotspot Notification Bot 🔥

แจ้งเตือนจุดความร้อน (Hotspot) จากดาวเทียม VIIRS ผ่าน LINE กลุ่ม

## ข้อมูลเบื้องต้น

- ดึงข้อมูลจุดความร้อนจาก [GISTDA API](https://api-gateway.gistda.or.th/)
- ส่งแจ้งเตือนเข้ากลุ่ม LINE ตามเวลาที่กำหนด (ค่าเริ่มต้น: 06:00 และ 14:00)
- รายงานเป็นภาษาไทย พร้อมลิงก์ Google Maps

## ขั้นตอนการติดตั้ง

### 1. สร้าง LINE Official Account & Messaging API

1. ไปที่ [LINE Developers Console](https://developers.line.biz/)
2. สร้าง Provider → สร้าง Messaging API Channel
3. ในแท็บ **Messaging API** → ออก **Channel Access Token** (long-lived)
4. ปิด **Auto-reply messages** (ตั้งเป็น Disabled)

### 2. หา Group ID ด้วย ngrok + Webhook Server

ใช้ `webhook_server.py` ร่วมกับ ngrok เพื่อจับ Group ID เมื่อเพิ่มบอทเข้ากลุ่ม

**Terminal 1** — รัน webhook server:

```bash
python webhook_server.py
```

**Terminal 2** — รัน ngrok:

```bash
ngrok http 8000
```

ngrok จะแสดง URL เช่น:

```
Forwarding  https://abcd-1234.ngrok-free.app -> http://localhost:8000
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

| ตัวแปร                      | คำอธิบาย                          | ตัวอย่าง      |
| --------------------------- | --------------------------------- | ------------- |
| `LINE_CHANNEL_ACCESS_TOKEN` | Token จาก LINE Developers Console | `xxxx...`     |
| `LINE_GROUP_ID`             | Group ID ของกลุ่ม LINE            | `C1234...`    |
| `GISTDA_API_KEY`            | API Key จาก GISTDA                | `LnCj76b...`  |
| `PROVINCE_IDN`              | รหัสจังหวัด (51 = ลำพูน)          | `51`          |
| `SCHEDULE_TIMES`            | เวลาแจ้งเตือน (คั่นด้วย ,)        | `06:00,14:00` |

## การใช้งาน

```bash
# รันแบบ Scheduler (แจ้งเตือนตามเวลาที่กำหนด)
python main.py

# รันทดสอบทันที 1 ครั้ง
python main.py --now
```

## การ Deploy

### ใช้ systemd (Linux)

```bash
# สร้างไฟล์ service
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

### ใช้ crontab

```bash
# แก้ไข crontab
crontab -e

# เพิ่มบรรทัด (รันทุก 06:00 และ 14:00)
0 6 * * * cd /path/to/line-hotspot-noti && /path/to/venv/bin/python main.py --now
0 14 * * * cd /path/to/line-hotspot-noti && /path/to/venv/bin/python main.py --now
```

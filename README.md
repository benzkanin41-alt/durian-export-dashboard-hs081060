# Dashboard ยอดส่งออกทุเรียน HS 081060

Static dashboard สำหรับติดตามยอดส่งออกทุเรียนของไทยจาก Thailand Trade Report กระทรวงพาณิชย์

Online dashboard:

https://benzkanin41-alt.github.io/durian-export-dashboard-hs081060/

## Coverage

- สินค้า: ทุเรียน
- HS code: `081060`
- HS name จาก MOC: `081060 : ทุเรียน`
- HS version: `2022`
- ช่วงข้อมูล: `2021-01` ถึง `2026-04`
- เดือนล่าสุดตาม source: `เม.ย. 2569`
- สกุลเงิน: บาท
- Grain หลัก: รายเดือน x ประเทศ

## Latest Snapshot

- มูลค่าเดือนล่าสุด: `37,328,305,001` บาท
- ปริมาณเดือนล่าสุด: `276,393,988` หน่วยตาม source
- YTD มูลค่า: `51,543,426,409` บาท
- YTD ปริมาณ: `378,167,459` หน่วยตาม source

## Dashboard Features

- KPI cards 6 ตัว: มูลค่า/ปริมาณเดือนล่าสุด, MoM, YoY, YTD value, YTD quantity
- Filter รายเดือน / รายไตรมาส / รายปี
- มุมมองรวมทุกประเทศ / รายประเทศ / รายทวีป
- Metric มูลค่า / ปริมาณ
- Growth MoM / YoY / QoQ ตามช่วงเวลาที่เลือก
- กราฟยอดส่งออกและกราฟ growth แบบ interactive
- จุดบนกราฟ click และ keyboard Enter/Space ได้
- ตาราง sortable พร้อม export CSV ตาม filter ปัจจุบัน
- Source & Validation section อยู่ท้ายหน้า

## Validation

- ดึงข้อมูลครบ `64` เดือน
- มี world summary row ครบ `64` เดือน
- รายประเทศรวม `2,894` country-month rows
- reconciliation max value diff = `0`
- reconciliation max quantity diff = `0`
- ไม่มีประเทศที่ map ทวีปไม่ได้

## Files

- `index.html` dashboard entrypoint
- `styles.css` dashboard styling
- `app.js` dashboard interaction and chart rendering
- `data.js` static dashboard payload for browser runtime
- `data/dataset.json` full processed dataset
- `data/monthly_country_hs081060.csv` monthly country-level data
- `data/monthly_continent_hs081060.csv` monthly continent-level data
- `data/monthly_total_hs081060.csv` monthly world total data
- `data/validation_reconciliation.csv` source reconciliation by month
- `qa-results.json` desktop/mobile QA results
- `dashboard-desktop-1440x1200.png` desktop QA screenshot
- `dashboard-mobile-390x1600.png` mobile QA screenshot

## Source

- Source page: https://tradereport.moc.go.th/th/stat/reporthscodeexport01
- Endpoint: `https://tradereport.moc.go.th/stat/reporthscodeexport01/result`
- Fetched UTC: `2026-06-10T12:55:46+00:00`

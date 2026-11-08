# Handoff rekaman demo MAC Flapping AIOps

Disiapkan 8 November 2026 dari konfigurasi published dan bukti eksekusi nyata.
Update verifier 8 November 09:34Z: kronologi clear kini mencakup awal insiden;
clear sebelum isolasi dicatat sebagai bukti yang sudah ada, bukan hasil AAP.
Semua jam lokal di dokumen ini memakai **UTC+7 / Asia/Bangkok**; timestamp JSON
berakhiran `Z` memakai UTC.

**Tujuan rekaman:** Scenario Controller → deteksi Nokia SR Linux → investigasi
Bits agent → approval manusia di Slack → AAP collect/isolate/verify → verifier
Datadog → notifikasi recovery → reset baseline.

**Batas pekerjaan penyusunan handoff:** hanya GET/read-only dan dokumentasi.
Tidak ada workflow yang dieksekusi, fault yang ditrigger, reset, perubahan monitor,
dashboard, koneksi, atau AAP. Langkah Run/Approve/Reset di bawah adalah instruksi
untuk sesi rekaman berikutnya, belum dijalankan oleh penyusunan dokumen ini.

## 1. Tab yang disiapkan

| Tab | URL langsung | Yang ditampilkan |
| --- | --- | --- |
| Scenario Controller | https://app.datadoghq.com/workflow/45ac61cf-8a35-4e2d-bed3-370ffc6a8506 | `[POC] Operational Scenario Controller v6 - AAP`, published, 98 steps; input `scenario` |
| Monitor MAC flapping | https://app.datadoghq.com/monitors/340593559 | Status OK/Alert, log count dalam 5 menit, sampel deteksi |
| Dashboard dan probe C→A | https://app.datadoghq.com/dashboard/rtw-gpm-4t5 | `[POC] MAC Flapping Lab - Full Observability`; widget **Host C to Host A packet loss (%)**, heartbeat dan status port |
| Metrics Explorer untuk memperbesar probe | https://app.datadoghq.com/metric/explorer | Tempel query probe di bagian 4, gunakan filter lab yang tepat |
| Workflow recovery | https://app.datadoghq.com/workflow/beb71b61-bff9-460d-ad37-853ae9cc778e | `[POC] Investigate Network MAC Flapping`, published, 101 steps; buka **run baru** dari alert |
| Log Explorer | https://app.datadoghq.com/logs?query=tags%3A%22service%3Anokia-srlinux%22%20env%3Anetwork-aiops%20host%3Asw1%20%22duplicate%20MAC%20address%22 | Deteksi dan deletion/clear untuk MAC serta target yang sama |
| AAP Jobs | https://192.168.2.66/execution/jobs | Filter ID job yang muncul di run baru; buka Output |
| Runbook Datadog | https://app.datadoghq.com/notebook/16202843 | Catatan implementasi dan bukti run |

Slack: siapkan **#datadog-workflow** untuk hasil Scenario Controller,
**#datadog-monitor** untuk notifikasi monitor, dan **#datadog-automation** untuk
analisis, approval serta hasil recovery. Pesan workflow dikirim sebagai pesan
channel tersendiri, mengikuti workflow existing; jangan menjanjikan semuanya ada
dalam satu thread monitor.

### Job Templates dan contoh job sukses

Job ID di tabel ini adalah **bukti historis**, bukan ID yang akan dipakai ulang.
Untuk rekaman baru, ambil ID aktual dari output workflow dan buka job tersebut.

| Tahap | Job Template | Output job sukses referensi |
| --- | --- | --- |
| Stop generator | [JT46](https://192.168.2.66/execution/templates/job-template/46/details) | [job355](https://192.168.2.66/execution/jobs/playbook/355/output) |
| Restore e1/2 sebelum start | [JT42](https://192.168.2.66/execution/templates/job-template/42/details) | [job357](https://192.168.2.66/execution/jobs/playbook/357/output) |
| Start generator | [JT45](https://192.168.2.66/execution/templates/job-template/45/details) | [job359](https://192.168.2.66/execution/jobs/playbook/359/output) |
| Collect evidence | [JT38](https://192.168.2.66/execution/templates/job-template/38/details) | [job361](https://192.168.2.66/execution/jobs/playbook/361/output) |
| Isolate Host B | [JT39](https://192.168.2.66/execution/templates/job-template/39/details) | [job363](https://192.168.2.66/execution/jobs/playbook/363/output) |
| Verify device | [JT40](https://192.168.2.66/execution/templates/job-template/40/details) | [job365](https://192.168.2.66/execution/jobs/playbook/365/output) |
| Verify forwarding | [JT41](https://192.168.2.66/execution/templates/job-template/41/details) | [job367](https://192.168.2.66/execution/jobs/playbook/367/output) |
| Reset: Stop → Restore → Verify | JT46 → JT42 → JT41 | [job370](https://192.168.2.66/execution/jobs/playbook/370/output) → [job372](https://192.168.2.66/execution/jobs/playbook/372/output) → [job374](https://192.168.2.66/execution/jobs/playbook/374/output) |

AAP memerlukan akses jaringan/VPN ke alamat privat dan sesi login sendiri. Rute
Output di atas mengikuti format AAP `/execution/jobs/playbook/<ID>/output`.
Jika UI/SSO mengembalikan halaman daftar, buka AAP Jobs lalu cari ID tersebut.
Fallback read-only untuk bukti JSON:
[job361](https://192.168.2.66/api/controller/v2/jobs/361/),
[job363](https://192.168.2.66/api/controller/v2/jobs/363/),
[job365](https://192.168.2.66/api/controller/v2/jobs/365/),
[job367](https://192.168.2.66/api/controller/v2/jobs/367/).

## 2. Prasyarat sebelum menekan Run

- Ubuntu Containerlab dan SW1/Host A/Host B/Host C berjalan. Baseline e1/1,
  e1/2, e1/3 **admin/oper up**, probe C→A **0% loss**, heartbeat **1**, monitor OK.
- Tidak ada generator terminal `run-continuous.sh` yang masih berjalan; JT46 hanya
  mengendalikan service `network-aiops-mac-flapping.service`.
- Private Action Runner online, dapat resolve `api.datadoghq.com` dan
  `config.datadoghq.com`, mengakses Datadog melalui HTTPS dan menjangkau AAP.
  Error DNS sebelumnya membuat dequeue dan health check gagal, meskipun container
  bertanda healthy. Bila perlu, cek log runner sebelum rekaman; jangan restart
  seluruh Docker/Containerlab sebagai bagian demo.
- Project AAP **37**, inventory **7**, kode generator tersinkron. JT45/46 memakai
  **Ubuntu Host SSH Credential, ID9**, prompted variables, dan sudo/root yang
  benar. Controller mengirim `ansible_become: true`, user `root`, metode `sudo`;
  tanpa itu uji awal job341 pernah gagal membuat direktori service.
- Koneksi Scenario Controller yang disepakati:
  `5c779fe2-0d2c-409d-8c1d-3319bf7d87e2`, akun
  `svc-datadog-fault-control` / user 4; Execute pada JT41/42/45/46.
  Recovery memakai koneksi existing `POC_AAP_CONNECTION_REMEDIATION`,
  `c501e5f5-17dd-4b5a-92d4-933a59b8f55f`, dengan akses JT38–41.
- Operator bisa membuka Datadog, AAP dan Slack, serta memilih approval di
  #datadog-automation. Selesaikan/reject approval lama sebelum take baru agar
  tidak mengisolasi port akibat klik pesan historis.
- Siapkan time range dashboard **Last 15 minutes**, auto-refresh, dan pin/fokus
  seri `ethernet-1/1`, `ethernet-1/2`, `ethernet-1/3`. Seri sub-interface
  `ethernet-1/2.1` berbeda dari interface fisik yang diisolasi.

**Snapshot read-only saat handoff:** 8 November, **15:41:53 lokal / 08:41:53Z**.
Controller 98 dan recovery 101 steps sama-sama published; dashboard 21 widgets
terbaca, monitor OK. Admin/oper ketiga port bernilai1 pada 08:41:30Z; loss 0,
heartbeat 1 dan keempat container up 1 pada 08:41:18Z. Ini snapshot, jadi operator
tetap memeriksa ulang tepat sebelum take. UI dan semua deeplink tidak diuji klik
dalam pekerjaan handoff ini; pemeriksaan konfigurasi/data dilakukan melalui API.

## 3. Urutan operator dan perpindahan layar

### A. Baseline, 30–60 detik rekaman

1. Buka dashboard. Tunjukkan loss 0%, heartbeat 1, empat container running dan
   ketiga port up/up. Buka monitor dan tunjukkan **OK**.
2. Buka Scenario Controller untuk memperlihatkan input serta alur network.
   Pastikan nilai yang dipilih nanti **`mac-flapping`**: default input saat ini
   adalah **`pool`**, dan `reset` adalah skenario lain.

Narasi: “Kita mulai dari lab sehat. Host A adalah endpoint tepercaya, Host B
menjadi sumber MAC duplikat, dan Host C menjadi probe independen.”

### B. Trigger dari Scenario Controller

Jalur operator yang sesuai trigger Slack yang sudah terpasang:

1. Di #datadog-workflow, ketik `/datadog workflow` dan buka pemilih workflow.
2. Pilih **[POC] Operational Scenario Controller v6 - AAP**.
3. Pada input **Scenario**, pilih **`mac-flapping`**, periksa sekali lagi, lalu
   klik **Run** pada dialog. Jalur manual Slack ini mengikuti dokumentasi Datadog;
   pastikan command tersedia untuk akun operator sebelum take.
4. Buka run baru di Scenario Controller/run history. Tunjukkan urutan
   **JT46 Stop → JT42 Restore → JT45 Start** dan pesan sukses di #datadog-workflow.
5. Pada output/artifact JT45, tunjukkan `macflap_generator_state=running`, PID
   positif, MAC `02:00:00:00:00:aa`, dan batas600 detik.

Jika halaman workflow menyediakan dialog Run, operator dapat mengisi input yang
sama dari sana. Jangan mengubah trigger, memilih step overrides, atau menjalankan
test dengan hasil mock untuk rekaman bukti nyata. Run sukses referensi di bawah
diluncurkan melalui agent trigger/MCP, bukan bukti pengujian klik UI Slack.

### C. Gangguan, alert dan investigasi

1. Pindah ke dashboard/probe dan Log Explorer. Cari log **`was detected`** untuk
   MAC yang sama pada `mac-flap` dan `ethernet-1/2.1`.
2. Buka monitor340593559 ketika berubah **Alert**. Perlihatkan count/sampel dan
   timestamp; jangan gunakan `DATADOG_SYSLOG_TEST` sebagai bukti duplicate MAC.
3. Dari notifikasi monitor atau run history recovery, buka **run baru** yang
   berhubungan dengan alert itu. Tunjukkan Report: `MAC_FLAPPING_EVIDENCE`,
   counts parsing dan target SW1. Uji referensi mengembalikan2 deteksi / 0 unparsed;
   run baru boleh mempunyai jumlah berbeda.
4. Tunjukkan ringkasan Bits agent di #datadog-automation. Loss dapat naik atau
   terputus-putus, tetapi jangan menjanjikan spike100%: tampilkan nilai aktual.
   Bukti gangguan minimum adalah log duplicate MAC nyata dan alert yang cocok.

### D. Approval Slack dan JT38–41

1. Di #datadog-automation, cocokkan link run, waktu alert dan target
   **sw1 · ethernet-1/2 (Host B)**. Buka pesan **03 AUTHORIZE** untuk run ini.
2. Klik **Approve AAP Isolation (JT 39)** sekali. Pilihan **Reject Remediation**
   menghentikan jalur tanpa job recovery; gunakan hanya untuk take penolakan.
3. Kembali ke run recovery. Tunjukkan `Record_Approval_Decision` = APPROVED.
4. Buka job aktual dari empat fase secara berurutan di AAP Output:
   **JT38 collect evidence → JT39 isolate e1/2 → JT40 verify device → JT41 verify
   forwarding**. Rekam status successful dan identitas template/job.
5. Di JT39, tunjukkan hanya e1/2 yang disable. Di JT40, port e1/1/e1/3 tetap up.
   Di JT41, tunjukkan ping Host C→Host A dengan 0% packet loss.

Approval berlaku1 jam, tetapi untuk take ini lakukan segera setelah memeriksa
target. Generator dibatasi10 menit; approval yang terlambat bisa membuat konteks
gangguan berubah. Jangan menekan Run/Approve berkali-kali saat job pending.

### E. Containment → verifier → notifikasi recovery

1. Dashboard: perlihatkan **e1/2 admin/oper 2 (down)** sebagai containment yang
   disengaja, sementara e1/1/e1/3 tetap 1 (up). Perlihatkan loss menuju0% dan
   heartbeat 1 dengan timestamp baru.
2. Workflow: buka `Evaluate_Recovery` pada iterasi terakhir, lalu
   `Finalize_Recovery_Verification` dan `Recovery_Verified`. Selama menunggu,
   perlihatkan `missing` yang masih ada; jangan menyebut recovery sudah verified.
3. Saat selesai, tunjukkan `verification.status=RECOVERY_VERIFIED`,
   `recovery_verified=true`, **13 criteria=true**, `missing=[]`, monitor OK,
   matched clear, serta quiet window 5 menit yang lolos.
4. Di #datadog-automation, tampilkan pesan **MAC Flapping — Telemetry Recovery
   Verified**, lalu cocokkan link run dan ID job. Pastikan
   `Slack_Recovery_Verified` successful serta `success_notification_sent=true`.

Narasi: “Recovery yang diverifikasi adalah containment dan forwarding, didukung
telemetry Datadog serta pasangan log clear. Port sumber tetap terisolasi.”
Jangan mengklaim physical loop terbukti atau tabel duplicate-MAC perangkat kosong
secara langsung. MonitorOK atau hilangnya log saja tidak cukup untuk klaim ini.

### F. Reset setelah hasil recovery direkam

1. Simpan bukti recovery terlebih dahulu. Selesaikan/reject approval lama yang
   masih menunggu dan pastikan tidak ada job isolasi yang masih berjalan.
2. Ulangi pemilih Scenario Controller, pilih **`reset-mac-flapping`**, klik Run.
3. Tunjukkan **JT46 Stop → JT42 Restore → JT41 Verify Forwarding** dan
   `ACTION_SUCCEEDED`, lalu pesan selesai di #datadog-workflow.
4. Dashboard: e1/2 kembali **up/up**, e1/1/e1/3 tetap up, loss 0%, monitor OK setelah
   evaluasi jendelanya. Artifact Stop harus `stopped` dan PID 0.

Reset adalah tindakan operator terpisah; recovery tidak otomatis mengaktifkan
kembali port. JT42 sendiri juga tidak menghentikan generator, sehingga gunakan
pilihan reset lengkap ini untuk menyiapkan take berikutnya.

## 4. Layar dan metric yang ditampilkan

| Fase | Layar utama | Bukti yang dicari |
| --- | --- | --- |
| Baseline | Dashboard + monitor | Admin/oper e1/1,e1/2,e1/3=1; loss 0%; heartbeat 1; container up 1; monitor OK |
| Gangguan | Log Explorer + monitor + probe | Dua bentuk target duplicate MAC, alert baru, loss aktual; sebelum isolasi port dapat tetap up |
| Containment | JT39/JT40 Output + dashboard | JT39 successful; e1/2 admin/oper 2; e1/1/e1/3 tetap 1; loss pulih |
| Recovery verified | Iterasi verifier terakhir + Slack |13 criteria=true; matched clear untuk semua target; quiet 5m; fresh stable post-job metrics; monitor OK; pesan Slack nyata |
| Reset | Controller + JT46/42/41 + dashboard | Service stopped/PID 0; e1/2 up/up; forwarding0%; ACTION_SUCCEEDED |

Query fokus untuk Metrics Explorer; gunakan `.fill(null)` agar gap tidak tampak
sebagai data sehat karena interpolasi:

```text
max:network_aiops.lab.probe.loss_pct{env:network-aiops,lab_id:macflap-v2,probe:host-c-to-host-a}.fill(null)
max:network_aiops.lab.collector.heartbeat{env:network-aiops,lab_id:macflap-v2}.fill(null)
max:snmp.ifAdminStatus{env:network-aiops,lab_id:macflap-v2,lab_device:sw1} by {interface}.fill(null)
max:snmp.ifOperStatus{env:network-aiops,lab_id:macflap-v2,lab_device:sw1} by {interface}.fill(null)
```

RTT `network_aiops.lab.probe.rtt_avg_ms` hanya pendukung;0%loss adalah syarat
forwarding verifier. Jangan jadikan chart container CPU/RAM yang kosong sebagai
bukti sehat; data itu pernah belum tersedia saat deployment dashboard.

Query log deteksi yang dipakai monitor:

```text
tags:"service:nokia-srlinux" env:network-aiops "duplicate MAC address" "was detected"
```

Untuk melihat deletion juga, hilangkan hanya frasa `"was detected"`, tambahkan
`host:sw1` dan filter MAC `"02:00:00:00:00:AA"`. Service reserved pada log dapat
bernama `sr_l2_mac_mgr`; filter `tags:"service:nokia-srlinux"` mempertahankan
tag service lab yang benar.

Verifier memerlukan minimal 2 sampel numerik per seri dengan rentang≥60 detik,
sesudah verification jobs selesai, umur≤180 detik, dan tidak ambigu. Pasangan clear
dicari sejak **awal insiden**, dengan target yang sama dan clear sesudah deteksi
terbarunya. Clear sebelum isolasi boleh memenuhi bukti kronologis, tetapi hasil
verifier dan pesan Slack menandainya sebagai PRE_ISOLATION serta tidak
mengatribusikannya ke AAP. Telemetry tetap wajib sesudah verification jobs.
Selanjutnya perlu 5 menit setelah clear terakhir tanpa deteksi baru. Verifier
polling 30 detik, maksimum 20 attempt atau deadline10 menit plus request in-flight;
kegagalan bukti/akses berhenti dan eskalasi ke Slack tanpa relaunch otomatis.

## 5. Waktu tunggu berdasarkan run nyata

Referensi 8 November, seluruh waktu lokalUTC+7:

| Milestone | Jam lokal | Waktu tunggu yang teramati |
| --- | --- | --- |
| Scenario Controller mulai |12:26:34.995 | Titik awal |
| Start/generator job359 selesai |12:29:04.253 | ±2m29s dari controller mulai |
| Controller sukses + Slack |12:29:21.241 | ±2m46s total trigger |
| Duplicate MAC pertama |12:29:12.993 | ±9s setelah job359 selesai |
| Recovery workflow otomatis mulai |12:30:20.407 | ±1m07s setelah deteksi |
| Approval tercatat |12:31:06.380 | ±46s setelah recovery mulai |
| JT39 selesai isolasi |12:32:49.197 | ±1m43s setelah approval |
| JT41 selesai forwarding |12:34:27.139 | ±3m21s setelah approval |
| Verifier lolos, attempt8 |12:39:31.505 | ±5m04s setelah JT41 selesai |
| Slack recovery successful |12:39:34.902 | Sesudah keputusan verifier |
| Recovery workflow selesai |12:39:36.014 | **±13m01s dari controller mulai** |

Reset terpisah terakhir:14:19:51.530 →14:22:20.346, **±2m29s**, jobs370/372/374.
Siapkan **20–25 menit untuk take mentah** termasuk baseline, approval operator,
perpindahan tab dan reset. Untuk video singkat, potong bagian menunggu dengan
keterangan waktu berlalu; jangan menyajikannya sebagai recovery instan.

Waktu di atas contoh terukur, bukan SLA. AAP project sync/queue bisa memperlama
pending; runtime playbook sendiri sering hanya 6–11 detik, tetapi jangan menyamakan
itu dengan keseluruhan waktu job. Polling AAP maksimal 60 kali dengan jeda 10 detik
per fase, di luar latensi request. JT41 dapat retry 30 kali dengan jeda 10 detik
selama hold-down. Generator berakhir otomatis setelah600 detik; run referensi
selesai sekitar saat batas generator tersebut, jadi jangan mengklaim generator
masih aktif pada frame akhir tanpa memeriksa service saat itu.

## 6. Bukti sukses dan lokasi dokumen

Dokumen handoff ini: **`lab-v2/docs/DEMO-RECORDING-HANDOFF.md`**.

| Bukti | Lokasi |
| --- | --- |
| Trigger controller sukses | [run2cec29b5](https://app.datadoghq.com/workflow/45ac61cf-8a35-4e2d-bed3-370ffc6a8506?instance=2cec29b5-e4ba-4e07-96f5-f8efe88a9343) |
| Full recovery verified dan Slack nyata | [run07dec5e0](https://app.datadoghq.com/workflow/beb71b61-bff9-460d-ad37-853ae9cc778e?instance=07dec5e0-d403-4d0e-ba7c-e6d7db4d30b6) |
| Reset terakhir sukses | [run2b10ddd0](https://app.datadoghq.com/workflow/45ac61cf-8a35-4e2d-bed3-370ffc6a8506?instance=2b10ddd0-9784-4232-b200-a6ca4b6dd5b2) |
| Snapshot full chain, approval, jobs,13 criteria, Slack ts | [scenario-controller-full-recovery-evidence.json](../../datadog/workflows/scenario-controller-full-recovery-evidence.json) |
| Bukti pengujian start/reset pertama dan koreksi sudo | [generator-controller-binding-evidence.json](../../datadog/workflows/generator-controller-binding-evidence.json) |
| Export published Scenario Controller | [operational-scenario-controller-v6-aap.json](../../datadog/workflows/operational-scenario-controller-v6-aap.json) |
| Export published recovery | [investigate-network-mac-flapping.json](../../datadog/workflows/investigate-network-mac-flapping.json) |
| Kebijakan verifier | [TELEMETRY-VERIFIER.md](TELEMETRY-VERIFIER.md) |
| Pengaturan AAP generator | [AAP-GENERATOR-SETUP.md](AAP-GENERATOR-SETUP.md) |
| Commit bukti full chain | [52e0936](https://github.com/avecenabasuni/mac-flapping-aiops/commit/52e0936) |

Untuk replay visual bukti lama, pilih absolute time 12:26–12:40 lokal 8 November 2026
(05:26–05:40 UTC) pada dashboard/logs. Sebut sebagai **rekaman bukti run sebelumnya**.
Pada take baru, gunakan run ID/job ID baru dan live time range. Artefak full chain
mencatat port masih terisolasi pada pemeriksaan sebelum restore; restore370/372/374
terjadi sesudahnya dan snapshot read-only handoff sudah menunjukkan baseline up.

Simpan dari take baru: controller run ID, recovery run ID, job IDs, waktu
Approve, hasil 13 criteria, bukti Slack berhasil terkirim dan reset run ID. Runtime
Datadog `SUCCEEDED` saja belum cukup: cek business result `RECOVERY_VERIFIED` dan
`success_notification_sent=true`. Jika `RECOVERY_NOT_VERIFIED`, rekam hasil
stop/escalation tersebut; jangan memakai screenshot sukses lama untuk menutupinya.

Rujukan UI tambahan: [manual Slack trigger Datadog](https://docs.datadoghq.com/actions/workflows/trigger/)
dan [format link Output AAP pada integrasi Jenkins plugin](https://github.com/jenkinsci/ansible-tower-plugin).
Tidak ada token, password atau SNMP community yang diperlukan dalam dokumen ini.

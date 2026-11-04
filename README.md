# MAC Flapping AIOps POC

Konfigurasi Datadog untuk Nokia SR Linux MAC flapping: log perangkat → parsing → monitor → investigasi Bits AI → ringkasan Slack.

## Isi

| File | Kegunaan |
| --- | --- |
| [Monitor](datadog/monitors/network-mac-flapping.json) | Log alert P3, hitung deteksi dalam 5 menit, threshold > 0. |
| [Workflow investigasi](datadog/workflows/investigate-network-mac-flapping.json) | Pengumpulan bukti, analisis Bits AI, dan ringkasan Slack. |
| [Scenario Controller v6](datadog/workflows/operational-scenario-controller-v6-aap.json) | Controller lengkap beserta skenario existing dan dua placeholder MAC flapping. |
| [Pipeline](datadog/pipelines/nokia-srlinux-mac-flapping.json) | Parsing empat format pesan detected/deleted pada MAC-VRF/sub-interface. |
| [Agent](datadog/agents/mac-flapping-evidence-analyst.json) | Prompt dan output schema analyst; akses MCP Datadog dinonaktifkan. |
| [Manifest](datadog/manifest.json) | ID sumber, waktu ekspor, dan hasil validasi live. |

Ekspor diambil dari konfigurasi tersimpan pada 2026-11-04T08:33:26Z. File adalah snapshot konfigurasi yang telah disesuaikan untuk repo publik; sesuaikan bentuk payload dengan API/tool yang dipakai saat impor.

## Konfigurasi ulang

- Ganti `AAP_CONTROLLER_HOST`, `REPLACE_WITH_DATADOG_CONNECTION_ID_1`, `REPLACE_WITH_SLACK_TEAM_ID`, dan `REPLACE_WITH_SLACK_DATADOG_MONITOR_CHANNEL_ID` dengan konfigurasi akun tujuan. Simpan autentikasi di Datadog Connections, bukan di repo.
- ID monitor, Bits agent, workflow, runbook, serta tautan Datadog dalam pesan/script masih merujuk deployment sumber. Saat membuat resource baru, perbarui referensi tersebut pada workflow dan pesan monitor.
- Sebelum menjalankan controller di akun tujuan, petakan ulang Job Template ID AAP untuk semua skenario existing. ID tersebut berasal dari lingkungan sumber.
- Bentuk pipeline mengikuti nama properti SDK. Konversikan ke bentuk payload API yang digunakan jika diperlukan. Buat pipeline sebagai resource baru ketika mengimpor ke akun lain.
- Konfigurasikan agent, pipeline, dan workflow; validasi dan publish workflow investigasi sebelum menghubungkan mention `@workflow-network-mac-flapping-investigation-poc` di blok alert monitor.

## Scenario Controller

Pilihan existing: `pool`, `disk`, `autoscale`, `rollback`, `memory`, `reset-memory`, `reset`.

Pilihan baru: `mac-flapping` dan `reset-mac-flapping`. Keduanya berhenti pada `JOB_NOT_CONFIGURED`, dengan ID job kosong; tidak mengirim request ke AAP. Job pemicu/reset MAC flapping akan disambungkan pada sesi AAP berikutnya. Keberhasilan runtime controller untuk placeholder tidak berarti job lab dijalankan: periksa `workflow_result`.

## Bukti validasi

Uji live 4 November 2026 berhasil: empat log baru memiliki parsing yang benar, monitor memicu workflow otomatis, laporan `COMPLETED / MAC_FLAPPING_EVIDENCE`, dan ringkasan Slack terkirim. [Lihat instance](https://app.datadoghq.com/workflow/beb71b61-bff9-460d-ad37-853ae9cc778e?instance=1f909fed-cf5f-46dd-a4ab-a3217adf4f63) dan [runbook](https://app.datadoghq.com/notebook/16202843).

Query menggunakan `tags:"service:nokia-srlinux"` karena reserved service pada log asli adalah `sr_l2_mac_mgr`. Frasa `"was detected"` memisahkan deteksi dari pesan `"is now deleted"`. Generic `DATADOG_SYSLOG_TEST` tidak memenuhi kondisi deteksi.

Monitor OK, pesan deletion, atau lima menit tanpa deteksi tidak membuktikan pemulihan perangkat. Workflow investigasi ini tidak menjalankan remediasi otomatis dan tidak membuktikan loop fisik. Penghitungan workflow dibatasi sampel 100 log; rate limit monitor satu run per 60 detik, tanpa penyimpanan deduplikasi lintas run.

## Lab v2: Continuous MAC Flapping and Controlled Recovery

The runnable Nokia SR Linux / Containerlab v2 implementation is in [lab-v2](lab-v2/README.md), including the continuous fault generator, Host C connectivity probe, AAP-safe isolation playbooks, and a [v1 to v2 migration guide](lab-v2/docs/MIGRATE-FROM-V1.md). The existing Datadog exports remain in the datadog/ directory. The v2 runtime and AAP execution have not yet been validated on the user's lab host.

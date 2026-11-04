# Monitoring switch dan perangkat lab v2

Paket lengkap seluruh lab, termasuk collector container/probe, template monitor dan dashboard, tersedia di [FULL-LAB-MONITORING.md](FULL-LAB-MONITORING.md). Dokumen ini berfokus pada pemasangan SNMP.

Status persiapan: template konfigurasi, belum dipasang pada VM/switch. Tidak ada monitor switch baru yang diklaim aktif.

Pemeriksaan Datadog pada sesi persiapan menemukan metrik sistem dari host `network-aiops-lab`, inventori NDM kosong, dan pencarian metrik SNMP belum menemukan data. Syslog dan investigasi MAC flapping sebelumnya sudah teruji pada v1. Temuan ini tidak membuktikan v2 sudah mengirim telemetry.

## Cakupan

| Objek | Sinyal yang dibutuhkan | Status |
| --- | --- | --- |
| SW1 | Keberhasilan polling SNMP, uptime dan identitas | Perlu konfigurasi SNMP |
| e1/1, e1/2, e1/3 | Admin/oper state, traffic, error/discard counters | Perlu validasi IF-MIB aktual |
| Host A/B/C | Port switch dan status/resource container masing-masing | Interface melalui SNMP; collector Docker tersedia dalam paket full-lab, belum dipasang |
| Ubuntu Containerlab | CPU, memory, disk, Agent health | Metrik CPU sudah terlihat; cakupan lain perlu dicocokkan dengan monitor existing |
| Host C → Host A | Packet loss dan latency pada data plane | Collector berkala tersedia dalam paket full-lab, belum dipasang |

CPU/RAM switch, sensor dan hardware counters hanya ditambahkan jika benar-benar diekspos perangkat/profil. SW1 virtual tidak otomatis memiliki seluruh sensor switch fisik. Ping management/SNMP yang sukses tidak membuktikan forwarding Host C → A sehat.

## File template

- [SNMP Agent](../../datadog/agent/snmp.d/conf.yaml.example)
- [Listener syslog](../../datadog/agent/syslog.d/conf.yaml.example)
- [Pengaktifan logs](../../datadog/agent/datadog.yaml.fragment.example)
- [Konfigurasi SNMP SR Linux](../monitoring/sw1-snmp.cli.example)

Agent minimal mengikuti prasyarat NDM Datadog (7.32+). Gunakan Agent di Ubuntu yang sudah menerima syslog. Tidak perlu Agent tambahan di setiap container endpoint untuk memonitor interface switch.

## Pemasangan pada lab

1. Temukan alamat management SW1 dan gateway v2 dari VM Ubuntu:

   ```bash
   sudo docker inspect clab-macflap-v2-sw1 --format '{{range .NetworkSettings.Networks}}{{println .IPAddress .Gateway}}{{end}}'
   sudo datadog-agent version
   ```

2. Pilih community khusus lab di konfigurasi lokal. Isi placeholder IP SW1 dan community di salinan SNMP Agent; isi juga community dan source-IP Agent pada contoh CLI switch. SNMPv2c ini ditujukan untuk management lab yang terisolasi; akses dibatasi ke source IP Agent. Contoh tidak berisi credential asli. SR Linux juga mendukung SNMPv3 untuk penggunaan yang membutuhkan auth/privacy.
3. Terapkan contoh CLI dari terminal SR Linux pada switch v2. Ini mengaktifkan polling management; tidak mengubah port data plane. Pastikan UDP 161 dapat dicapai dari Ubuntu Agent dan prefix-list sesuai source IP yang benar-benar terlihat oleh switch.
4. Gabungkan template SNMP ke `/etc/datadog-agent/conf.d/snmp.d/conf.yaml`. Pertahankan instance existing. Profil awal `generic-device` mengumpulkan MIB standar; bukan jaminan seluruh OID didukung Nokia ini. Periksa warning dan metric/interface yang benar-benar dikirim sebelum membuat alert.
5. Listener UDP 10514 existing tetap dipakai. Gabungkan tags lab v2 pada listener yang sama jika memang hanya digunakan lab ini; jangan membuat listener duplikat. Jangan mengganti API key/site atau konfigurasi Agent lain.
6. Jalankan pemeriksaan lalu restart Agent setelah konfigurasi benar:

   ```bash
   sudo datadog-agent configcheck
   sudo systemctl restart datadog-agent
   sudo datadog-agent check snmp
   sudo datadog-agent status
   ```

7. Periksa Network Devices di Datadog dan metric/tag dari namespace `network-aiops-lab-v2`. Cocokkan interface name/index dengan e1/1–e1/3 dan pastikan nilai admin/oper sesuai CLI switch.

## Aturan monitor setelah telemetry tersedia

- SNMP collection failure: kondisi sumber telemetry gagal, bukan langsung menyimpulkan switch mati. Korelasikan dengan management reachability dan Agent health.
- Unexpected interface down: admin enabled tetapi oper down, khusus port lab yang dipetakan. e1/1 dan e1/3 harus tetap aktif.
- Intentional isolation: e1/2 admin disabled merupakan state containment yang disengaja saat demo. Rekam pada dashboard/evidence; jangan memicu alert kerusakan yang sama dengan link putus saat admin enabled. Kondisi admin-disabled di luar demo tetap perlu peninjauan terpisah.
- Traffic/errors/discards: gunakan counter/rate dan tags yang ditemukan setelah ingestion; tetapkan threshold setelah melihat baseline lab.
- Endpoint/container availability: harus melihat status container yang diharapkan, bukan hanya jumlah seluruh container di host. Koneksi Docker Agent pada Ubuntu belum diverifikasi.
- Host C → A: gunakan probe data plane independen dari collector full-lab. Script ping/hasil AAP sendiri tidak otomatis menjadi metric Datadog. Tidak membuat metric palsu dari log monitor OK.

Pada tahap ini tidak ada perubahan pada placeholder job AAP `mac-flapping` / `reset-mac-flapping`, workflow investigasi, atau monitor MAC flapping existing.

## Acuan resmi

- https://docs.datadoghq.com/network_monitoring/devices/snmp_metrics/
- https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example
- https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/default_profiles/generic-device.yaml
- https://documentation.nokia.com/srlinux/25-3/books/system-mgmt/snmp.html

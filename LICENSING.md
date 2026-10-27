# Lisensi dan asal kode

Script, pengaturan build, dokumentasi, dan perubahan milik proyek menggunakan GPL-2.0-only. Kode driver asal mempertahankan copyright ST-Ericsson, kredit penulis, serta pilihan lisensi GPL versi 2 atau BSD 2-Clause. Distribusi modul dalam proyek ini menggunakan GPLv2 tanpa menghapus pemberian lisensi atau hak cipta kode asal. Saat mendistribusikan ulang, sertakan teks lisensi, pemberitahuan copyright, dan source code yang sesuai dengan kewajiban GPLv2.

Header `cdc_ncm.c` memuat pemberitahuan perubahan sesuai GPLv2 pasal 2(a), berisi nama pengubah, tanggal perubahan (2026-10-27), dan daftar perubahan. Modul hasil modifikasi dideklarasikan dengan `MODULE_LICENSE("GPL")`, sehingga versi modifikasi secara keseluruhan hanya ditawarkan di bawah GPL-2.0-only. Pilihan lisensi BSD 2-Clause berlaku untuk kode asal ST-Ericsson saja.

## Dasar perubahan

Perbandingan dengan Linux v6.8 menunjukkan tiga perubahan pada driver: pemeriksaan status endpoint hanya diwajibkan untuk perangkat yang memerlukannya, penanganan interface NCM Apple tanpa status endpoint, serta pencocokan vendor `05ac` dengan product ID `1905` dan `1902` pada interface 0 dan 2. Bagian driver lainnya sesuai dengan sumber pembanding tersebut.

## Atribusi upstream

Pendekatan kompatibilitas terkait tersedia pada [dukungan interface Apple](https://github.com/torvalds/linux/commit/3ec8d7572a69) oleh Ole André Vadla Ravnås dan Håvard Sørbø, serta [dukungan jaringan USB Mac](https://github.com/torvalds/linux/commit/a5148bc2fa27092862ac4b9e7b5c8340d60cff34) oleh Alex Cheema. Referensi ini menjelaskan dasar teknis dan atribusi, tanpa menyatakan seluruh riwayat proyek diimpor dari upstream. Repository ini tidak menyertakan firmware Apple atau binary proprietary macOS.

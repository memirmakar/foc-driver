# FOC Motor Sürücü — Devir (Handover) Dokümanı · Rev B

**Repo:** https://github.com/altinay10/foc-motor-driver (commit `4a430fc`)
**Tarih:** 2026-10-02
**Bu dokümanın amacı:** PCB tasarımını ve komponent değişikliği işini devralacak kişinin, önceki
analiz ve kararları baştan çıkarmak zorunda kalmadan işe başlayabilmesi.

Ekler (bu klasörde):
- `BOM_revB.csv` — revize malzeme listesi (fiyat kaynağı, durum, alternatif sütunlarıyla)
- `FOC-surucu-analiz.md` — ayrıntılı teknik denetim ve fiyat taraması

---

## 1. Proje özeti

Kapalı çevrim FOC motor sürücü kartı.

| Özellik | Hedef |
|---|---|
| Motor tipleri | 2 faz bipolar step (ana hedef), 3 faz BLDC/PMSM, fırçalı DC |
| Güç katı | 4 yarım köprü (HB1–HB4) = 2 H-köprü |
| Bara | 36–48 V |
| Akım | 5 A sürekli/faz, 15 A tepe dayanım |
| Akım ölçümü | In-line shunt + INA240A2, HB1 ve HB3 çıkışında |
| Açı | Kart üstü AS5047D (14 bit, SPI), harici SPI encoder, **yeni:** ABI/Hall girişi |
| Haberleşme | CAN-FD (FDCAN + TJA1051T/3), papatya dizimi |
| PWM | 30 kHz merkez hizalı (20–50 kHz parametre) |
| PCB | 4 katman, hedef 45×45 mm (sığmazsa 50×50) |

Motor eşleşmesi:

| Mod | Bağlantı | Akım ölçümü |
|---|---|---|
| Step | A sargısı HB1–HB2, B sargısı HB3–HB4 | A: RS1, B: RS2 |
| BLDC | U=HB1, V=HB2, W=HB3 (HB4 boşta) — **üç faz da U3'te, tek DRV8300 ile çalışır** | U ve W (V = −U−W) |
| DC | 1–2 adet çift yönlü: HB1+HB2, HB3+HB4 | Her motor için bir shunt |

---

## 2. Repo'nun mevcut durumu (devralırken bilinmesi gerekenler)

| Öğe | Durum |
|---|---|
| `docs/DESIGN.md`, `docs/site/foc-anatomi.html` | Kapsamlı ve büyük ölçüde doğru. **Rev A'yı anlatıyor**, bu dokümandaki Rev B değişiklikleri işlenmedi |
| `hardware/*.kicad_sch` | **~%10–15 tamam.** Sadece MCU, 1× MIC4605, 2× FET, AS5047D, kristal, birkaç C var |
| `hardware/*.kicad_pcb` | **Boş** |
| `hardware/BOM.csv` | Rev A. Yerine `BOM_revB.csv` kullanılacak |
| `firmware/` | Yok (başlanmadı) |
| `simulation/current_loop.py` | Çalışıyor ama **gerilim sınırı modeli hatalı** (bkz. §7) |

Şematikteki tutarsızlıklar:
- MCU sembolü `STM32G474RBTx`. Rev A dokümanı `G431CBT6` diyordu. **Rev B kararı: STM32G431RBT6** (LQFP-64; pin uyumlu sembol `STM32G431RBTx`).
- Net etiketi olarak `PSMQC094N10NS2` kullanılmış (parça numarasına benziyor). Doğru net adlarıyla değiştirilmeli.
- LM5163 (veya LMR38010) için KiCad sembolü yok, çizilmeli. DRV8300 sembolü KiCad standart kütüphanesinde yoksa o da çizilmeli.

---

## 3. Kararlar

### 3.1 Kesinleşenler
| # | Karar | Gerekçe |
|---|---|---|
| K1 | 4 yarım köprü topolojisi | Step 2 faz; aynı donanımla BLDC ve DC |
| K2 | MCU ailesi STM32G4 kalıyor, F4'e geçilmiyor | F4'te CAN-FD, dahili komparatör→BKIN ve CORDIC yok; üstelik daha pahalı ve stoksuz |
| K3 | **Fren chopper kaldırıldı** (Q9, UCC27517, J5 çıktı) | Proje kararı. Etkisi için bkz. §6 R5 |
| K4 | In-line akım ölçümü ve INA240A2 korunuyor | Kalite. Low-side + dahili OPAMP daha ucuz ama yüksek modülasyonda ölçüm penceresi daralıyor |
| K5 | Bootstrap gate sürüşü (charge pump yok) | Tutma torku PWM ile üretiliyor (duruşta duty ≈ %42/%58), %100 duty gerekmiyor |
| K6 | Kapasitör azaltarak maliyet düşürülmeyecek | EMI ve aşırı gerilim |
| K7 | **Sürücü dağılımı: U3 = HB1+HB2+HB3, U4 = HB4** (2026-10-03) | BLDC kartı tek DRV8300 ile üretilebilsin (U4, Q7, Q8 ve HB4 parçaları DNP). Bedeli: step modunda B sargısının iki bacağı farklı entegrede (§4.2) |

### 3.2 Önerilen, onay bekleyen
| # | Öneri | Not |
|---|---|---|
| O1 | **4× MIC4605 → 2× DRV8300DPWR** | Rev A'daki MIC4605-**1** zaten yanlış varyanttı (çift giriş). DRV8300: sabit 150–280 ns dead-time + çapraz iletim kilidi, dahili bootstrap diyotu, ~2.6 $ ucuz |
| O2 | Alternatif: 2× **DRV8353/DRV8350** | FET başına VDS aşırı akım izleme ve fault pini. Daha pahalı; TR kanallarında stok yok. Fiyat araştırılmadı |
| O3 | **STM32G431RBT6** (LQFP-64) | 8 PWM + ABI/Hall + BKIN2 için pin gerekli. Farnell'de CBT6'dan ucuz |
| O4 | 12 V buck → **LM5163** (100 V) | LMR38010'un 80 V mutlak maksimumu TVS kıstırma gerilimi altında kalıyor. DigiKey stoku 0, tedarik kontrol edilmeli |

### 3.3 Açık (karar verilmeli)
- Ters polarite P-FET parça numarası (≥100 V, gate zener'li)
- Bulk kapasitör parça numarası (100 V, ripple akımı hesabına göre)
- Konnektör ailesi (J1/J2 akımı: zincirdeki **toplam** kart akımını taşıyacak)
- GVDD yük anahtarı parçası (§4.4)
- Termal çözüm: soğutucu / motor flanşına termal pad / fan (§4.6)

---

## 4. PCB tasarımcısı için

### 4.1 Rev B blok yapısı
```
48V ─ J1/J2 ─ Q10 ters polarite (P-FET + zener) ─ D1 TVS ─ C_BULK (100V) ─┬─ HB1..HB4 (Q1-Q8)
                                                                           │     └─ alt FET source'lari ─ RS3 (bara shunt) ─ GND
                                                                           └─ U7 LM5163 ─ 12V ─┬─ U10 yuk anahtari ─ GVDD ─ U3 (HB1-3) / U4 (HB4) DRV8300
                                                                                               └─ U8 LMR51430 ─ 3.3V ─ MCU, INA240, CAN, AS5047D
                                                                                                                  └─ FB1 ─ 3.3VA (ADC ref, INA240 REF1, encoder)
```

### 4.2 Gate driver yerleşimi (DRV8300)
- **U3 = HB1 + HB2 + HB3, U4 = HB4 (K7).** BLDC'de U/V/W üç fazı aynı entegrede (kanallar arası gecikme eşleşmesi ±30 ns); BLDC varyantında U4 ve HB4 takılmaz.
- **Bedeli:** step modunda B sargısı (HB3–HB4) iki entegreye bölünür; entegreler arası gecikme farkı 110 ns'ye kadar çıkabilir. 48 V / 30 kHz'te bu ~0.16 V ortalama gerilim hatası demek, büyük ölçüde sabit ofset; kapalı çevrim akım döngüsü (PI integratörü) telafi eder. Firmware'de dead-time kompanzasyonuna bacak başına ofset kalibrasyonu eklenmeli.
- **U3 ve HB1–HB3 FET'leri** birlikte yerleşmeli; U4 HB4'ün yanında durur.
- **Fren chopper (opsiyonel, DNP):** U4 kanal B alt çıkışı (GLB) → Q9 + J9; kontrol BRK_PWM (PB6, TIM8_CH1). U4 kanal C kullanılmıyor. BLDC varyantında (U4 yok) chopper da yoktur.
- **BLDC varyantı DNP listesi:** U4, Q7, Q8, U4 GVDD kondansatörleri, HB4 gate ağı, HB4 bootstrap ve C_HB kondansatörleri. Şematikte bu parçalarda `Variant` alanı dolu. Firmware, U4 takılı değilken step modunu engellemeli.
- GH/SH ve GL/GND döngüleri kısa olmalı. Bootstrap kondansatörü BSTx–SHx pinlerinin dibine konmalı. GVDD'ye ≥10 µF.
- DRV8300'ün tek GND pini var (alt gate dönüşü de buradan). GND'yi alt FET source bölgesine kısa yoldan bağlayın; RS3 bara shunt'ının hangi tarafına referanslanacağını yerleşimde netleştirin (öneri: driver GND = RS3'ün GND tarafı, alt FET source'ları RS3'ün üst tarafı; gate dönüş yolu shunt üzerinden geçer ama düşüm mV mertebesinde).
- Gate direnci: turn-on 33 Ω, turn-off 10 Ω + diyot. **FET'in kapanma süresi 150 ns'nin (min dead-time) altında kalmalı.** Turn-off direnci büyütülmemeli.
- Girişlerde (INHx/INLx) dahili pull-down var. Yine de MCU reset durumunda köprünün kapalı kaldığını doğrulamak için hatlara harici 10–100 kΩ pull-down konabilir.

### 4.3 Akım ölçümü ve koruma
- RS1/RS2: **Kelvin** bağlantı, INA240 girişlerine kısa, sıkı ve GND korumalı diferansiyel çift.
- INA240 **REF1 → 3.3VA** (dijital 3V3'e değil). REF2 → AGND.
- **RS3 (yeni):** tüm alt FET source'ları → RS3 → GND. G431 dahili OPAMP (PGA) → dahili COMP → TIM1_BKIN. Böylece HB2/HB4 kısa devresi, FET delinmesi ve shoot-through yakalanır (in-line shunt'lar bunları görmez).
- Faz akımı sinyalleri **COMP_INP olabilen pinlere** atanmalı (§5).

### 4.4 Donanımsal ENABLE (önemli, Rev A'dan farklı)
DRV8300'de EN pini **yok**. Bu yüzden ENABLE şöyle uygulanmalı:
1. Harici ENABLE (J6) → **TIM1_BKIN2** pini: CPU'dan bağımsız olarak timer çıkışlarını idle'a (tüm FET'ler kapalı) çeker.
2. Harici ENABLE **AND** MCU_EN (U11, 74LVC1G08) → **U10 GVDD yük anahtarı**: 12 V gate besleme kesilir, DRV8300 UVLO'ya girer, tüm FET'ler kapanır. MCU kilitlense bile çalışır.
3. ENABLE hattına pull-down: konnektör çıkarılırsa sürücü kapalı kalmalı.

### 4.5 Güç katı ve EMI
- Her bacakta **2× 2.2 µF 100 V X7R 1210** (C_HB), üst FET drain ile alt FET source arasında, mümkün olan en küçük döngüde.
- Güç döngüsü: bulk → üst FET → alt FET → RS3 → GND, en küçük alan. 4 bacak birbirinin kopyası olarak yerleşmeli.
- Katman dizilimi (Rev A'dan): Sinyal/Güç — **kesintisiz GND** — GND/Güç — Sinyal. GND düzlemi bölünmeyecek.
- Encoder ve analog bölge anahtarlamadan fiziksel olarak ayrı; besleme FB1 üzerinden.
- **AS5047D alt yüzde, kartın tam merkezinde** (mıknatısla hizalı). Yerleşim buradan başlar.

### 4.6 Termal
- Tahmini kayıp 3.3 W (30 kHz) – 4.7 W (50 kHz). 45×45 mm'de doğal konveksiyonla **+55…80 °C** artış bekleniyor → soğutma şart.
- FET altlarında termal via tarlası, iç katman bakırları geniş tutulmalı.
- NTC (RT1) FET bakırına yakın.
- Montaj delikleri / termal pad alanı soğutucu veya motor flanşı için planlanmalı.

### 4.7 CAN ve konnektörler
- J1/J2: 48 V + GND + CANH + CANL. Akım değeri zincirdeki toplam akıma göre seçilmeli.
- CAN: **split terminasyon** (2× 60.4 Ω + 4.7 nF, jumper ile seçilebilir) + **PESD2CANFD** ESD.
- J5 (fren direnci) kaldırıldı.
- **J8 (yeni):** ABI encoder / Hall, 5 pin: 5V, GND, CH1, CH2, CH3. Her hatta seri direnç + 3.3 V'a klemp, seçilebilir pull-up (open-collector Hall için).
- Q10 P-FET: gate-source 12–15 V zener + seri direnç (48 V, V_GS ±20 V sınırını aşar).
- Sıcak takma (hot-plug) ani akımı için soft-start/inrush sınırlama değerlendirilmeli.

---

## 5. MCU sinyal listesi (STM32G431RBT6) — pin haritası CubeMX'te yapılacak

Rev A'daki LQFP-48 haritası **geçersiz.** Aşağıdaki sinyaller ve kısıtlarla CubeMX'te yeni harita çıkarılmalı.

| Sinyal | Adet | Çevrebirim | Kısıt |
|---|---|---|---|
| PWM INH/INL HB1–HB3 | 6 | TIM1 CH1/CH1N, CH2/CH2N, CH3/CH3N | Complementary + DTG |
| PWM INH/INL HB4 | 2 | TIM1 CH4/CH4N **veya** TIM1'e senkron TIM8 | CH4N pin müsaitliğini doğrula |
| Faz A akımı | 1 | ADC + **COMP_INP** | COMP3_INP = PA0/PC1, COMP1_INP = PA1/PB1, COMP2_INP = PA7/PA3, COMP4_INP = PB0 |
| Faz B akımı | 1 | ADC + **COMP_INP** | Rev A'daki PA4 COMP girişi değildi, **kullanılmamalı** |
| Bara akımı (RS3) | 1 | OPAMP VINP → dahili COMP → TIM1_BKIN | OPAMP giriş pinini doğrula |
| Harici ENABLE | 1 | TIM1_BKIN2 + GPIO | + U11 AND kapısına |
| MCU_EN | 1 | GPIO out | U11'e |
| FDCAN1 RX/TX | 2 | FDCAN1 | PB8 kullanılırsa `nSWBOOT0 = 0` option byte |
| SPI1 (AS5047D) | 4 | SPI1 | |
| SPI2 (harici encoder) | 4 | SPI2 | |
| ABI/Hall (J8) | 3 | TIM3 veya TIM4 CH1–CH3 | Encoder modu + Hall (XOR) arayüzü aynı timer'da |
| VBUS, NTC, CAN adres | 3 | ADC | |
| USART2 debug | 2 | USART2 | |
| GPIO giriş ×2, aux çıkış ×1 | 3 | GPIO | Aux = Q11 |
| LED ×2 | 2 | GPIO | |
| SWD, OSC_IN/OUT, NRST | 5 | | |

---

## 6. Bilinen sorunlar ve riskler

| # | Sorun | Önem | Durum |
|---|---|---|---|
| R1 | MIC4605-1 yanlış varyant (çift giriş); tek PWM planıyla köprü çalışmazdı | Kritik | DRV8300 ile çözülüyor (O1) |
| R2 | Faz B'de donanım aşırı akım koruması yok (PA4 COMP girişi değil), A'da tek yönlü | Kritik | Pin haritası + RS3 ile çözülecek |
| R3 | HB2/HB4 kısa devresi ve shoot-through hiçbir sensörde görünmüyor | Kritik | RS3 bara shunt'ı (yeni) |
| R4 | ENABLE yazılıma bağlıydı | Kritik | §4.4 |
| R5 | **Chopper kaldırıldı** → rejenerasyonda bara gerilimi yükselir, TVS sürekli enerjiyi kaldıramaz | Yüksek | Firmware: VBUS izleme, yavaşlama rampası sınırı, gerekirse sıfır vektör frenleme. Opsiyonel chopper footprint (§4.2) |
| R6 | Gerilim koordinasyonu: 63 V kapasitör, SMBJ58A kıstırma 93.6 V > LMR38010 80 V | Yüksek | 100 V kapasitör, SMCJ54A, LM5163 |
| R7 | Termal: soğutmasız +55…80 °C | Yüksek | §4.6 |
| R8 | DRV8300 sabit 150–280 ns dead-time → bacak başına ~0.3 V bozulma | Orta | Firmware'de dead-time kompanzasyonu (kalibrasyonlu) |
| R9 | DRV8300'de fault pini, VDS izleme, sıcaklık koruması yok | Orta | RS3 + NTC + firmware; ya da O2 (DRV8353) |
| R10 | Simülasyon gerilim sınırı hatalı → hız tavanı ~%30 iyimser (571 → ~405 rpm) | Orta | §7 |
| R11 | CAN terminasyonu ve ESD yoktu | Orta | BOM'a eklendi |
| R12 | Bootstrap %100 duty'de dolamaz | Düşük | Firmware duty sınırı %97–98 |

---

## 7. Firmware'e etki eden donanım kararları

- **Duty sınırı:** SVPWM dahil %97–98 (bootstrap yenilenmesi için ≥0.5–1 µs off süresi).
- **Bootstrap ön şarj:** Her enable'da ve Hi-Z sonrasında alt FET'ler kısa süre açılmalı.
- **Dead-time:** MCU DTG yedek amaçlı (ör. 50–100 ns). Etkin dead-time ~215 ns (driver). Akım yönüne göre gerilim kompanzasyonu gerekir.
- **nSWBOOT0 = 0** option byte (FDCAN RX PB8'e düşerse) — ilk programlamada.
- **Chopper yok:** VBUS eşik izleme, rejeneratif frenlemede akım/rampa sınırı.
- **Simülasyon düzeltmesi:** `current_loop.py` içindeki `max_current_at_speed` dq'da kare değil daire sınırı kullanmalı: `(R·iq + ωe·λm)² + (ωe·L·iq)² ≤ Vbus²`. λm tutma torkundan türetilirken `|i| = √2·I_anma` alınmalı (tutma torku iki faz birden enerjiliyken ölçülür).

---

## 8. Komponent değişikliği iş paketi

Ayrıntı `BOM_revB.csv` içinde. Fiyatlar 2026-10-02 taramasından, 10 adet kademesi.

**Sonuç:** komponent toplamı Rev A **~61.5 $ → Rev B ~48.5 $** (PCB hariç). Bu toplamın ~22 $'ı "TAHMIN" veya "BOM tahmini" kaynaklı; doğrulanması gerekiyor.

Tedarik notları:
- **Özdisan:** Çoğu parça stoksuz, "Fiyat ve Stok Talep Et". Stoklu ve en ucuz olduğu kalem CSD19534Q5A (0.46 $, 474 adet). DRV8300DPWR 0.47 $ (talep üzerine).
- **DigiKey:** MCU, INA240, DRV8300, TJA1051 stoklu. CSD19534Q5A sadece 3 adet, LM5163 stok 0.
- **Farnell TR:** G431RBT6 en ucuz burada (10+: 4.79 €). DRV8300 ve LMR38010 yok. INA240A2 sadece TSSOP (A2PWR).
- AS5047D artık Infineon markasıyla satılıyor: DigiKey `AS5047D-ATST-TSSOP14`. Farnell'deki ams AS5047D-ATSM "üretimden kaldırıldı".

Yapılacaklar:
- [ ] "TAHMIN" ve "ACIK" satırlarının parça numarası ve fiyatını netleştir (Q10, Q11, C_BULK, U10, D1, D12, konnektörler)
- [ ] LMR51430'u doğrula; 150 mA yük için daha küçük/ucuz bir buck değerlendir
- [ ] LM5163 stoğu yoksa LM5164 veya başka bir 100 V buck seç (LMR38010 ancak TVS stratejisi değişirse)
- [ ] O1/O2 kararı: DRV8300 mü DRV8353 mü (DRV8353 fiyat/stok araştırması)
- [ ] Bulk kapasitör ripple akımı hesabı (2 H-köprü, 5 A, 30 kHz)
- [ ] Her parça için KiCad sembol + footprint (proje kütüphanesine, `${KIPRJMOD}` ile)
- [ ] BLDC (tek sürücü) varyantı için ayrı BOM / montaj varyantı (K7)

---

## 9. Bring-up ve doğrulama listesi

1. Saat, SWD, LED, UART; `nSWBOOT0 = 0`; CAN bağlıyken normal boot.
2. GVDD yük anahtarı ve ENABLE zinciri: ENABLE düşünce GVDD'nin kesildiğini ölç.
3. Motorsuz, düşük bara geriliminde (12–24 V) PWM: her bacakta **V_GS(üst) ve V_GS(alt) aynı anda** osiloskopla → dead-time ve turn-off < 150 ns doğrulaması. Sonra 48 V'ta ve sıcakken tekrar.
4. RS3 + COMP → BKIN: kontrollü kısa devre testi (akım sınırlı kaynakla).
5. INA240 ofset kalibrasyonu (PWM açık, motor bağlı değil).
6. AS5047D ham açı → açık çevrim döndürme → encoder↔elektriksel açı kalibrasyon tablosu.
7. Akım döngüsü (tork modu), dead-time kompanzasyonu ayarı.
8. Hız ve pozisyon döngüsü; tutma torku testi (5 A, duruşta, termal gözlem).
9. Rejeneratif frenleme testi: chopper yokken VBUS yükselmesini ölç.
10. İki kartla CAN-FD papatya dizimi.

---

## 10. Kaynaklar
- DRV8300 datasheet (TI SLVSFG5D): https://www.ti.com/lit/ds/symlink/drv8300.pdf
- MIC4605 datasheet (Microchip DS20005853): https://download.mikroe.com/documents/datasheets/mic4605.pdf
- STM32G431 datasheet: https://www.mouser.com/datasheet/2/389/stm32g431c6-1600866.pdf
- Fiyat/stok: digikey.com, tr.farnell.com, ozdisan.com (2026-10-02)

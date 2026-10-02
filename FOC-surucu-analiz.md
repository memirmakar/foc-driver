# FOC Motor Sürücü (altinay10/foc-motor-driver) — Teknik Denetim ve Maliyet Analizi

Tarih: 2026-10-02 · İncelenen commit: `4a430fc` (Initial import)

---

## 0. Kontrol listesi (neye bakıldı)

| # | Konu | Sonuç |
|---|---|---|
| 1 | Repo durumu (şematik / PCB / firmware olgunluğu) | ⚠️ Erken aşama |
| 2 | Gate driver seçimi ve pin planı tutarlılığı | ❌ **Kritik hata** |
| 3 | Dead-time / shoot-through koruması | ⚠️ Kısmen |
| 4 | Aşırı akım / kısa devre koruması | ❌ Boşluk var |
| 5 | ENABLE / güvenli durma | ❌ Yazılıma bağlı |
| 6 | Gerilim koordinasyonu (TVS, kapasitör, regülatör, driver) | ❌ Tutarsız |
| 7 | Ters polarite / hot-plug / daisy-chain gücü | ⚠️ Eksik detay |
| 8 | Akım ölçüm zinciri (INA240, referans, ADC) | ✅ İyi, küçük düzeltme |
| 9 | MCU seçimi, pin bütçesi, çevrebirim eşleşmesi | ⚠️ Pin yetmiyor |
| 10 | Simülasyon / hız-tork zarfı hesabı | ❌ Hesap hatası |
| 11 | Termal bütçe | ⚠️ Soğutmasız tutmaz |
| 12 | CAN-FD arayüzü | ⚠️ Terminasyon/ESD yok |
| 13 | 4 yarım köprü / step motor desteği | ✅ |
| 14 | BLDC desteği | ✅ FOC için, sınırlamalarla |
| 15 | DC motor desteği (donanım değişmeden) | ✅ Sınırlamalarla |
| 16 | G4 → F4 değişimi | ❌ Önerilmez |
| 17 | 4× MIC4605 → 2× DRV8300 | ✅ Uygulanabilir, önerilir |
| 18 | Fiyat/stok (DigiKey, Farnell, Özdisan) | Aşağıda |

---

## 1. Genel değerlendirme

**Tasarım düşüncesi güçlü, donanım uygulaması henüz yok denecek kadar az.**

- `docs/DESIGN.md` ve `foc-anatomi.html` iyi yazılmış; topoloji (4 yarım köprü), in-line shunt + INA240,
  50 kutup çifti etkisi, encoder kalibrasyon zorunluluğu, anti-windup, dq ileri besleme gibi kararlar doğru.
- **Ama:**
  - Şematikte sadece ~30 sembol var: 1× MIC4605, 2× FET, MCU, AS5047D, kristal, birkaç kapasitör.
    Güç katı, akım ölçümü, CAN, regülatörler, konnektörler **çizilmemiş**.
  - Şematikteki MCU sembolü **STM32G474RBTx (LQFP-64)**, dokümandaki ise **STM32G431CBT6 (LQFP-48)** — tutarsız.
  - Net etiketi olarak `PSMQC094N10NS2` kullanılmış (parça numarasına benziyor, net adı değil).
  - PCB dosyası boş (80 bayt), firmware klasörü yok.
  - BOM'daki fiyatlar EKOM'dan ve birçok satır "ACIK" (parça seçilmemiş).

Sonuç olarak "ne kadar iyi" sorusunun cevabı: **konsept seviyesinde 7/10, uygulanabilir donanım seviyesinde
henüz değerlendirilemez.** Aşağıdaki kritik hatalar düzeltilmeden kart basılırsa çalışmaz ya da güvenli olmaz.

---

## 2. Kritik bulgular (kart basılmadan önce düzeltilmeli)

### 2.1 ❌ MIC4605-1 yanlış varyant — tasarım bu haliyle çalışmaz
BOM: `MIC4605-1YM … tek PWM girişi`. Datasheet (DS20005853):
- **MIC4605-1 = çift giriş (HI + LI)**
- **MIC4605-2 = tek PWM girişi**

Tasarımın pin planı tek PWM + ortak EN (4 PWM + 1 EN). -1 ile LI pini 300 kΩ dahili pull-down ile
sürekli düşük kalır → alt FET hiç açılmaz → bootstrap kondansatörü dolmaz → üst FET de sürülemez.
**Çözüm:** ya MIC4605-**2** (aynı fiyat, aynı kılıf), ya da aşağıdaki DRV8300 + LQFP-64 seçeneği.

### 2.2 ❌ Aşırı akım koruması pin eşleşmesi tutmuyor
Doküman: "COMP → TIM1_BKIN, harici parça yok". STM32G431'de komparatör pozitif girişleri:
COMP1_INP = PA1/PB1, COMP2_INP = PA7/PA3, COMP3_INP = PA0/PC1, COMP4_INP = PB0/PE7.
- Faz A akımı **PA0** → COMP3 ✓ (ama yalnız **tek yön**; stepte akım çift yönlü)
- Faz B akımı **PA4** → **hiçbir komparatörün INP'si değil** ✗ → B fazında donanım OCP yok.
- Her pin yalnız bir komparatöre gidiyor → çift yönlü (±) eşik için ya sinyali iki pine bağlamak ya da
  ayrı bir bara akımı ölçümü gerekir. (Pin eşleşmesini CubeMX'te teyit edin.)

### 2.3 ❌ HB2 / HB4 ve shoot-through için hiç koruma yok
Shunt'lar yalnız HB1 ve HB3 çıkışında. Şu arızaları **hiçbir sensör görmez**:
- A− veya B− terminalinin GND'ye / VBUS'a kısa devresi (akım HB2/HB4 FET'inden geçer, shunt'tan geçmez)
- Köprü içi shoot-through ya da delinmiş FET (in-line shunt köprü içi akımı görmez)

**Çözüm (ucuz):** DC bara dönüşüne tek bir low-side shunt (2–5 mΩ) + G431'in dahili OPAMP'ı (PGA) +
dahili COMP → TIM1_BKIN. ~0.5 $ ek maliyet, tüm köprü arızalarını ve bara akımını kapsar.
Bonus: bara akımı ölçümü güç/rejenerasyon kestirimi ve fren chopper kontrolü için de işe yarar.

### 2.4 ❌ "Donanımsal ENABLE" aslında yazılımsal
Harici ENABLE girişi PB7'ye (GPIO in) gidiyor; driver EN'i PB6'dan MCU sürüyor. MCU kilitlenirse veya
firmware hatası varsa ENABLE düşse bile köprü kapanmaz. DESIGN.md §11'deki "Sertifikalı STO yerine
donanımsal ENABLE yeterli" iddiası bu şemayla geçersiz.
**Çözüm:** ENABLE'ı (a) bir 74LVC1G08 AND kapısıyla driver EN hattına donanımsal olarak bağlayın,
(b) ayrıca TIM1_BKIN2 pinine verin. EN ve PWM hatlarına pull-down koyun (reset/boot sırasında MCU pinleri
yüzerken köprü kapalı kalsın).

### 2.5 ❌ Gerilim koordinasyonu tutarsız
| Eleman | Değer |
|---|---|
| Bara | 36–48 V (13S Li-ion dolu: **54.6 V**) |
| Fren chopper devreye girme | ~54 V ← 13S dolu batarya ile çakışır |
| SMBJ58A | V_BR min **64.4 V**, kıstırma V_C **93.6 V** (@I_pp) |
| Bulk kapasitör | **63 V** ← TVS iletime geçmeden aşılır |
| LMR38010 | abs max **80 V** ← TVS kıstırması bunu aşar |
| MIC4605 HS | abs max 90 V |

**Çözüm:** Kapasitörleri 80–100 V'a çıkarın; 12 V buck'ı 100 V'luk LM5163/LM5164'e geçirin (fiyat aynı);
TVS'i SMCJ54A gibi daha yüksek I_pp'li bir parçayla değiştirin ki kıstırma gerilimi düşük kalsın;
asıl aşırı gerilim koruması fren chopper'dır, eşiğini parametre yapın.

### 2.6 ❌ Simülasyondaki gerilim sınırı hatalı → hız tavanı ~%30 iyimser
`simulation/current_loop.py` gerilim sınırını **dq çerçevesinde kare** alıyor (|v_d| ≤ Vbus ve |v_q| ≤ Vbus
ayrı ayrı). Bağımsız H-köprülerin kare sınırı **sabit αβ çerçevesindedir**; dq çerçevesi döndükçe bu kare
de döner, her açıda garanti olan sınır içteki dairedir: √(v_d² + v_q²) ≤ Vbus.

Yeniden hesap (NEMA23, R=1.5 Ω, L=3 mH, 48 V, 5 A):

| λm varsayımı | Model | Tam akımın korunduğu son hız |
|---|---|---|
| 13.6 mWb (repo) | kare (repo) | 9.5 dev/s (571 rpm) |
| 13.6 mWb (repo) | **daire (doğru)** | **6.75 dev/s (405 rpm)** |
| 9.6 mWb | daire | 7.8 dev/s (471 rpm) |

Ek not: λm tutma torkundan `T/(p·I)` ile türetilmiş. Tutma torku iki faz birden anma akımındayken
ölçülür, bu yüzden |i| = √2·I_anma alınmalı; böyle hesaplanınca λm ≈ 9.6 mWb olur. Tablodaki 3.39 N·m
gibi değerler de 2.8 A'lik bir motoru 5 A'de lineer kabul ediyor; doyum nedeniyle gerçekte daha düşük çıkar.

---

## 3. Dead-time koruması — tam mı?

**Kısa cevap: Tam değil.** Tek katmanlı ve doğrulanmamış.

| Katman | Mevcut tasarım (MIC4605-2 varsayımıyla) |
|---|---|
| MCU dead-time (TIM1 DTG) | **Yok.** Tek PWM girişli driver'da complementary çıkış kullanılmıyor |
| Driver dead-time | Adaptif: HS→LS geçişinde switch node (HS < 2.2 V) izleniyor ✓; LS→HS geçişinde ise **LO pin** gerilimi (< 1.9 V) izleniyor |
| Driver interlock | Var (tek PWM girişiyle iki çıkışın birden açık olması mantıksal olarak imkânsız) ✓ |
| Arıza geri bildirimi | Yok (MIC4605'te fault pini yok) |
| Shoot-through algılama | Yok (bkz. 2.3) |

**Zayıf nokta:** LO pini 1.9 V'un altına indiğinde FET kapısı hâlâ yüksek olabilir, çünkü arada
10 Ω + diyot + FET'in iç R_g'si var. Datasheet de harici sönümleme direncinin kapanma gecikmesini
artırdığını açıkça yazıyor. Datasheet'teki dead-time < 20 ns. Pratikte bu yönde marjı sağlayan şey,
üst FET'in 33 Ω üzerinden yavaş açılması — bu da tesadüfi bir marj, tasarlanmış değil.

**Ek riskler:**
- %100 duty'de bootstrap şarj olamaz. `duty = 0.5 + v/(2·Vbus)` doyumda 1'e gider → firmware'de
  %95–97 ile sınırlanmalı.
- Adaptif dead-time akım yönüne ve sıcaklığa göre değiştiği için, düşük hızda gerekli olan
  dead-time kompanzasyonu daha zor (sabit bir dead-time ile deterministik olurdu).

**Önerilen çözüm (çift katman):**
complementary PWM + MCU DTG (ör. 100–150 ns) **+** driver'ın kendi interlock'u.
Bunun için DRV8300D (6x giriş, sabit 200 ns + cross-conduction engeli) veya MIC4605-1 (HI/LI, adaptif +
"ilk açılan kazanır" kilidi) kullanılabilir — ikisi de yarım köprü başına 2 pin ister → LQFP-64 MCU.
Bring-up'ta her köprüde V_GS(alt) ile V_GS(üst) aynı anda osiloskopla ölçülmeli.

---

## 4. 4× MIC4605 yerine 2× DRV8300 olur mu?

Önce bir düzeltme: Mevcut tasarımda her MOSFET için ayrı driver yok, **her yarım köprü için bir driver**
var (8 FET'e 4 driver). DRV8300 tek pakette **3 yarım köprü** sürer → 2 adet = 6 kanal.

**Evet, olur ve önerilir.** Kanal dağılımı:

| Kanal | Kullanım |
|---|---|
| 1–4 | HB1–HB4 |
| 5 (yalnız low-side) | Fren chopper FET'i → **UCC27517 kalkar** |
| 6 | Yedek (ör. ikinci low-side çıkış) |

| | 4× MIC4605-2 | 2× DRV8300DPW |
|---|---|---|
| Gerilim | HS 90 V abs | SHx 85 V çalışma, BST 125 V abs, SHx −22 V tolerans |
| Dead-time | Adaptif (~20 ns) | Sabit 200 ns (TSSOP) + cross-conduction engeli |
| Giriş | 1 PWM / köprü | 2 giriş / köprü (6x) → **MCU dead-time + bacak başına Hi-Z** |
| Bootstrap diyot | Dahili | Dahili (D versiyonu) |
| Gate akımı | 1 A | 0.75 A kaynak / 1.5 A çekme (zaten R_g ile yavaşlatılıyor) |
| Fiyat (10 adet) | 4 × 1.05 $ = **4.20 $** (DK) | 2 × 0.81 $ = **1.62 $** (DK); Özdisan 0.47 $/adet |
| UCC27517 | Gerekli (~0.6–1.2 $) | Gereksiz |

**Bedeli:** 8 PWM hattı gerekiyor. LQFP-48'de pin kalmadığı için **STM32G431RBT6 (LQFP-64)** gerekir —
Farnell'de CBT6'dan daha ucuz (aşağıda). Dördüncü köprü için TIM1_CH4/CH4N veya TIM1 ile senkronize
TIM8 kullanılabilir (CubeMX'te teyit edin).

Varyant notu: `DRV8300DPWR` = INL non-inverting (6x complementary PWM için doğru seçim, en çok stoklu).
`DRV8300DIPWR` = INL inverting (INH=INL bağlanırsa tek-PWM modu, ama DigiKey'de daha pahalı).

---

## 5. 4 faz / step + BLDC + DC motor desteği

### 5.1 Step motor (2 faz bipolar, 4 yarım köprü) — ✅ Tam destek
TIM1 CH1–CH4 bağımsız, iki H-köprü, iki in-line shunt. 6/8 telli unipolar motorlar bipolar olarak bağlanabilir.

### 5.2 BLDC (3 faz) — ✅ FOC için evet, kısıtlarla
- HB1/HB2/HB3 = U/V/W; shunt'lar U ve W'de, V = −(U+W). FOC + SVPWM için yeterli.
- **Kısıtlar:**
  - Ortak EN olduğu için bacak başına Hi-Z yok → 6-step trapez ve BEMF sıfır geçişli sensörsüz çalışma yapılamaz (sensörlü ya da gözlemcili FOC yapılabilir).
  - **Hall girişi yok** (J6'da yalnız 2 giriş var, 3 gerekir, 5 V seviye koruması da yok).
  - Açı ölçümü yalnız kart üstü AS5047D (mıknatıs kartın merkezine hizalı olmalı) veya SPI harici encoder ile.
  - Faz gerilimi ölçümü yok (sensörsüz başlatma / flying start zorlaşır).
- DRV8300 + LQFP-64 önerisi bu kısıtların ilk ikisini kaldırır.

### 5.3 DC motor (donanım değiştirmeden) — ✅ Evet, kısıtlarla
- 1 adet çift yönlü fırçalı DC: HB1+HB2, akım RS1 ile ölçülür ✓ (tork/akım kontrolü, rejeneratif fren).
- 2 adet çift yönlü DC: HB1+HB2 ve HB3+HB4, her birinde bir shunt ✓.
- 4 adet tek yönlü DC (her yarım köprüden GND'ye) yapılabilir, ama yalnız ikisinin akımı ölçülür.
- **Kısıtlar:**
  - **Quadrature (ABI) encoder girişi yok** — çoğu DC redüktörlü motorda ABI encoder var → pozisyon kontrolü için donanım değişikliği gerekir (LQFP-64 ile TIM3/TIM4 encoder modu).
  - Ortak EN yüzünden köprü başına "coast" (serbest bırakma) yok; yalnız fren (iki bacak aynı duty) mümkün.
  - 4 mΩ shunt ile ölçüm aralığı ±8.25 A; yüksek akımlı DC motor için 2 mΩ seçeneği var.

---

## 6. G431 yerine F4? — ❌ Önerilmez

| MCU | CAN | CORDIC/FMAC | Dahili COMP→BKIN | DigiKey 10 ad. | DigiKey 100 ad. | Stok (DK) |
|---|---|---|---|---|---|---|
| **STM32G431CBT6** (mevcut) | **FDCAN (CAN-FD)** | ✓ | ✓ (4×) | 5.39 $ | 4.53 $ | 280 |
| **STM32G431RBT6** (öneri, LQFP-64) | FDCAN | ✓ | ✓ | 5.43 $ | 4.57 $ | 6575 |
| STM32G431C8T6 (64 KB) | FDCAN | ✓ | ✓ | 4.40 $ | 3.68 $ | 18 |
| STM32F446RET6 | bxCAN (FD yok) | ✗ | ✗ | 7.98 $ | 6.78 $ | 0 |
| STM32F405RGT6 | bxCAN (FD yok) | ✗ | ✗ | 9.78 $ | 8.35 $ | 0 |

F4'ler **daha pahalı**, stokta yok ve README'deki CAN-FD papatya dizimi şartını karşılamıyor.
F401/F411 gibi ucuz F4'lerde hiç CAN yok. G4 bu iş için hem en ucuz hem en doğru aile.
**Öneri:** G431**RB**T6 — Farnell'de CBT6'dan ucuz (10+: 4.79 € vs 5.66 €), stok bol ve pin sorununu çözüyor.
(Şematikte zaten LQFP-64 G474 sembolü var; G474 gereksiz pahalı, G431RB yeterli.)

---

## 7. Diğer bulgular (orta / düşük öncelik)

1. **Termal:** 3.3–4.7 W kayıp, 45×45 mm kartta doğal konveksiyonla ~16–25 K/W → **+55…80 °C** artış.
   Motor flanşına termal pad ile ısı yolu, küçük bir soğutucu ya da hava akışı şart. Alternatif olarak dV/dt
   0.5 yerine ~1.2 V/ns hedeflenirse anahtarlama kaybı düşer.
2. **INA240 REF1 → +3.3 V (dijital)**, ADC referansı ise +3.3VA (FB1 ile filtreli). REF1'i 3.3VA'ya
   bağlayın; ratiometrik olsun, dijital gürültü ofset olarak ölçüme binmesin.
3. **Low-side yerine in-line seçiminin gerekçesi yanlış ifade edilmiş:** Tasarımın kendi modülasyonunda
   (duty = 0.5 + v/2Vbus) duruşta duty ≈ %50, yani low-side penceresi en geniş. Low-side ölçümün kör
   kaldığı yer **yüksek modülasyon**, düşük duty değil. In-line yine de daha iyi bir seçim (pencere kısıtı yok),
   INA240'ı koruyun — sadece dokümandaki gerekçe düzeltilmeli.
4. **Yarım köprü başına lokal 100 V MLCC** (ör. 2× 2.2 µF 1210 X7R) BOM'da açıkça yok ("PASIF" içinde
   kaybolmuş). EMI ve aşırı gerilim sıçraması için zorunlu — **maliyet düşürme sırasında kesinlikle çıkarılmamalı.**
5. **Ters polarite P-FET:** 48 V'ta V_GS ±20 V'u aşar → gate–source zener (12–15 V) + seri direnç gerekli.
   Daisy-chain'de hot-plug ani akımı (bulk kapasitör şarjı) konnektörde ark yapar → soft-start veya
   inrush sınırlayıcı (ör. LM74700 + FET ya da NTC) düşünün. Papatya dizimindeki ilk konnektörden
   N kartın toplam akımı geçer; konnektör akım sınıfını buna göre seçin.
6. **CAN:** Terminasyon (split 2×60 Ω + jumper/switch) ve CAN ESD diyotu (ör. PESD2CANFD) yok.
   TJA1051'in ±58 V bus hata toleransı 48 V ile aynı konnektör için iyi bir seçim ✓.
7. **SW1 (BOOT/RESET SPDT) + 10 kΩ → BOOT_PIN:** nSWBOOT0=0 yaklaşımında BOOT0 pinine gerek yok ve PB8
   CAN RX ile paylaşımlı. Kaldırın ya da NRST butonuna çevirin.
8. **Ripple formülü (§4.4):** İki bacak aynı taşıyıcıyla merkez hizalı sürüldüğünde sargı 3 seviyeli ve 2f'de
   görür → ΔI ≈ Vbus/(8·L·f). Gerçek ripple dokümandakinin yarısı (lehte bir hata).
9. **Pin bütçesi:** 33/35 dolu; harici ABI encoder, Hall, bacak başına EN, bara akımı ve BKIN2 için yer yok → LQFP-64.
10. **AS5047D artık Infineon markasıyla satılıyor** (DigiKey: `AS5047D-ATST-TSSOP14`); Farnell'de ams
    AS5047D-ATSM "üretimden kaldırıldı" görünüyor. Parça numarasını güncelleyin.

---

## 8. Fiyat / stok taraması (2026-10-02)

Fiyatlar: DigiKey USD, Farnell TR EUR (KDV hariç), Özdisan USD (KDV hariç). Değerler sitelerde görülen
kademeli fiyatlardır; anlık değişebilir.

| Parça | BOM (EKOM) | DigiKey | Farnell TR | Özdisan |
|---|---|---|---|---|
| STM32G431CBT6 | 5.24 $ | 1: 7.04 · 10: 5.39 · 100: 4.53 $ (stok 280) | 1: 7.39 · 10: 5.66 · 100: 4.61 € (stok 2424) | stok 0, talep üzerine |
| **STM32G431RBT6** | — | 1: 7.08 · 10: 5.43 · 100: 4.57 $ (stok 6575) | 1: 6.25 · **10: 4.79** · 100: 4.03 € | stok 0, talep üzerine |
| STM32G431C8T6 | — | 1: 5.78 · 10: 4.40 · 100: 3.68 $ (stok 18) | — | listelenmiyor |
| MIC4605-1YM-TR | 1.26 $ | 1–10: 1.05 · 100: 0.86 $ (stok 2460) | 1: 0.91 · 100: 0.74 € (stok 2054) | stok 0 (-1YM-T5) |
| MIC4605-2YM(-TR) | — | 1–10: 1.05 · 100: 0.86 $ (stok 2170) | 1: 0.90 · 100: 0.73 € (stok 475) | — |
| **DRV8300DPWR** | — | 1: 1.12 · 10: 0.81 · 100: 0.65 $ (stok 6160) | yok | **1: 0.47 · 100: 0.44 $** (stok 0, talep) |
| DRV8300DIPWR | — | 1: 1.65 · 10: 1.21 · 100: 0.97 $ (stok 991) | yok | — |
| INA240A2D / A2DR | 4.54 $ | A2D: 10: 2.85 · 100: 2.40 $ (stok 7317); A2DR stok 0 | A2PWR (TSSOP): 10: 2.24 · 100: 1.85 € (stok 1292) | A2DR stok 0, talep |
| INA241A2IDR | — | 10: 2.59 · 100: 2.14 $ (stok 0) | — | — |
| AD8418AWBRZ | — | 10: 3.30 $ (stok 78) | — | — |
| AS5047D | 8.92 $ | Infineon AS5047D-ATST: 1: **6.80 $** (stok 4500) | AS5047D-ATSM: üretimden kaldırıldı | AS5047D-ATSM stok 0 |
| MA732GQ-Z (alternatif) | — | 1: 4.81 · 10: 4.13 · 100: 3.61 $ (stok 1678) | — | — |
| LMR38010SDDAR | 3.94 $ | 1: 2.97 · 10: 2.22 · 100: 1.83 $ (stok 615) | yok | yok |
| LM5163DDAR (100 V) | — | 10: 2.25 · 100: 1.85 $ (stok 0) | — | stok 0, talep |
| UCC27517DBVR | 1.24 $ | UMW muadili: 0.40 $ @10 | — | yok |
| TJA1051T/3 | 1.98 $ | /3/2Z: 10: 1.23 · 100: 0.99 $ (stok 6793) | /3/1J: 10: 1.14 · 100: 0.93 € (stok 6380) | yok |
| CSD19534Q5A | 0.55 $ | 10: 0.995 · 100: 0.66 $ (stok **3**) | Q5AT: 10: 1.19 · 100: 1.02 € (stok 265) | **1: 0.46 · 100: 0.43 $ (stok 474)** |

**Tedarikçi gözlemi:** Özdisan bu parçaların çoğunda stoksuz ("Fiyat ve Stok Talep Et"); stoklu ve en ucuz
olduğu kalem CSD19534Q5A. MCU ve analog için DigiKey/Farnell, FET için Özdisan en mantıklı kombinasyon.

---

## 9. Maliyet düşürme önerileri (kaliteyi düşürmeden)

| Değişiklik | Eski | Yeni (≈10 adet) | Fark/kart | Kalite etkisi |
|---|---|---|---|---|
| 4× MIC4605 + UCC27517 → 2× DRV8300DPWR | 5.04 + 1.24 = 6.28 $ | 1.62 $ (DK) / 0.94 $ (Özdisan) | **−4.7…−5.3 $** | + (MCU dead-time + interlock, bacak başına Hi-Z) |
| INA240A2: EKOM → DigiKey/Farnell | 9.08 $ | 5.70 $ / ~4.9 $ | **−3.4…−4.2 $** | Aynı parça |
| AS5047D: EKOM → DigiKey (Infineon) | 8.92 $ | 6.80 $ | **−2.1 $** | Aynı parça |
| LMR38010: EKOM → DigiKey (ya da LM5163 100 V) | 3.94 $ | 2.22–2.25 $ | **−1.7 $** | LM5163 ile **+** (100 V marj) |
| TJA1051T/3: EKOM → DK/Farnell | 1.98 $ | 1.23 $ / 1.14 € | **−0.75 $** | Aynı |
| CSD19534Q5A ×9: Özdisan | 4.95 $ | 4.17 $ | −0.8 $ | Aynı |
| MCU: G431CBT6 → G431RBT6 | 5.24 $ | 5.43 $ (DK) / 4.79 € (FA) | ≈0 | + (pin sorunu çözülür) |
| **Toplam tasarruf** | | | **≈ −13…−15 $/kart** | |
| Eklenmesi gerekenler (bara shunt, AND kapısı, CAN ESD + terminasyon, pull-down'lar, zener, 100 V kapasitörler) | | | **+1.5…2.5 $** | Güvenlik için zorunlu |
| **Net** | ~61.5 $ | **~49–51 $** | **≈ −11…−12 $ (≈ %18–20)** | Kalite artar |

**Önerilmeyen (kaliteyi düşürür):**
- INA240 → low-side shunt + G4 dahili OPAMP (~4–5 $ tasarruf, ama yüksek modülasyonda ölçüm penceresi daralır).
- AS5047D → MA732 (~2.7 $ ek tasarruf; ama 50 kutup çiftinde açı hatası 50 kat büyüdüğü için doğruluk kritik. Kullanılacaksa mutlaka kalibrasyonla).
- Bulk/lokal kapasitör azaltma — EMI ve aşırı gerilim sıçraması artar.
- UMW "UCC27517" muadili — kaynağı belirsiz; DRV8300'e geçilince zaten gereksiz.

---

## 10. Öncelikli yapılacaklar listesi

1. [ ] Driver kararını verin: **(A)** MIC4605-2 + mevcut pin planı (minimum değişiklik) veya **(B, önerilen)** 2× DRV8300DPWR + G431RBT6 + complementary PWM + MCU dead-time.
2. [ ] Bara akımı için low-side shunt + OPAMP + COMP → BKIN; faz akımlarını COMP_INP pinlerine yeniden atayın.
3. [ ] ENABLE'ı donanımsal yapın: AND kapısı + BKIN2; EN ve PWM hatlarına pull-down.
4. [ ] Gerilim koordinasyonu: 100 V kapasitörler, 100 V buck (LM5163/4), TVS seçimini ve chopper eşiğini revize edin.
5. [ ] `current_loop.py`'deki gerilim sınırını daireye çevirin; λm'yi √2 düzeltmesiyle yeniden türetin.
6. [ ] Termal yolu tanımlayın (soğutucu / motor flanşı / fan).
7. [ ] CAN terminasyonu + ESD; ters polarite FET'ine zener; inrush sınırlama.
8. [ ] Şematiği tamamlayın (doküman ile şematikteki MCU tutarsızlığını giderin, net adlarını düzeltin).
9. [ ] ABI encoder + Hall girişi (LQFP-64 ile) — DC ve BLDC desteği için.
10. [ ] Bring-up'ta dead-time ölçümü: her köprüde V_GS(üst) ve V_GS(alt) aynı anda, tam akım ve sıcakken.

---

### Kaynaklar
- MIC4605 datasheet (Microchip DS20005853) — https://download.mikroe.com/documents/datasheets/mic4605.pdf
- DRV8300 datasheet (TI SLVSFG5D) — https://www.ti.com/lit/ds/symlink/drv8300.pdf · https://www.ti.com/product/DRV8300
- STM32G431 COMP pin eşleşmesi — https://www.mouser.com/datasheet/2/389/stm32g431c6-1600866.pdf · https://community.st.com/t5/stm32-mcus-products/stm32g431-comparator-bug/td-p/675832
- Fiyat/stok: digikey.com, tr.farnell.com, ozdisan.com (2026-10-02 tarihli tarama)
